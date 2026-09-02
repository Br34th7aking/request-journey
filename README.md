# request-journey

Following an HTTP request through every layer of a production-style web stack — nginx (load balancer + cache) → Gunicorn → Django → Postgres — and measuring what each layer contributes.

The premise: the further down the stack a request travels, the more it costs. A response served from a cache at the edge is orders of magnitude cheaper than one rendered by Python against a database, so a fast site serves as much traffic as possible **as high up the stack as possible**. This repo demonstrates that with numbers.

```
browser / wrk
      │
      ▼
┌─────────────┐   :80 (published as :8000)
│    nginx    │   load balancer + web accelerator (10s microcache)
└──────┬──────┘
       │ round robin, unless cached
   ┌───┴────┐
   ▼        ▼
┌──────┐ ┌──────┐   :8000 each (web1 also published as :8001 for direct benchmarks)
│ web1 │ │ web2 │   Gunicorn × 2 workers → Django
└───┬──┘ └──┬───┘
    └───┬───┘
        ▼
   ┌─────────┐
   │ Postgres│      100k seeded rows; the dashboard runs a deliberately
   └─────────┘      expensive aggregate + ORDER BY random()
```

Two pages exercise the accelerator's core question — *"is this response the same for everyone?"*:

- `/` — generic dashboard (aggregates over 100k rows). Same for everyone → nginx microcaches it for 10s.
- `/me/` — per-user visit counter (session-based). Never cached; any request carrying a `sessionid` cookie also **bypasses** the cache for `/` (`proxy_cache_bypass` / `proxy_no_cache`).

## Results

Apple-silicon MacBook Pro, Docker Desktop. Treat numbers as relative, not absolute — the whole stack shares one VM.

### Single request (idle system)

| Layer that answered | Typical time |
|---|---|
| nginx cache HIT | **~0.7 ms** |
| Full Django render, via nginx (cache bypassed) | **~21 ms** |
| Full Django render, Gunicorn direct | **~22–38 ms** |

### Under load — `wrk -t2 -c10 -d15s`

| Target | Req/s | Avg latency | Total requests in 15s |
|---|---|---|---|
| Gunicorn direct (web1 only, 2 workers) | 97 | 102 ms | 1,463 |
| nginx, cache **bypassed** (LB across 4 workers) | 187 | 53 ms | 2,817 |
| nginx, cache **HIT** | **31,323** | **0.53 ms** | 472,966 |

## Findings

1. **The cache is worth ~170× the full stack.** 31,323 vs 187 req/s. During the 15s cached run Django rendered the page 2–3 times (initial MISS + 10s TTL expiry); the other ~473k responses cost Python nothing. Serving traffic from as high up the stack as possible isn't an optimization — it's the difference between hundreds and tens of thousands of req/s.
2. **Accidental proof that load balancing works.** "Direct" and "bypassed" were expected to tie; instead bypassed doubled throughput (97 → 187 req/s) and halved latency (102 → 53 ms) — because direct hits only web1's 2 workers while nginx round-robins across web1+web2 = 4 workers. Double the lanes, half the queue.
3. **The proxy hop is free.** Per-request render time via nginx (~21 ms) matches Gunicorn direct. The accelerator layer costs nothing on a miss and saves everything on a hit.
4. **Latency under load is queueing, not rendering.** A render takes ~20 ms, yet direct wrk showed 102 ms average: 10 connections contending for 2 workers means most of a request's life is spent waiting in line. More workers (finding 2) or fewer trips to Django (finding 1) both attack the queue, not the render.
5. **Per-user pages defeat caching by design.** With a `sessionid` cookie every request goes to Django (`X-Cache: BYPASS`) — correctness over speed. The shared cache entry stays live for anonymous visitors; the cookie only routes *that visitor* around it.

## Run it yourself

```bash
docker compose up -d --build
docker compose exec web1 python manage.py migrate
docker compose exec web1 python manage.py seed     # 100k rows
```

Then:

- watch the cache: `curl -sI localhost:8000/ | grep X-Cache` twice → `MISS` then `HIT`; in a browser, the page's "rendered at" timestamp freezes for 10s at a time
- watch the bypass: visit `/me/` once (sets a session cookie), then `/` re-renders on every refresh
- watch the round robin: refresh `/me/` — `X-Served-By` alternates between the two backends
- benchmark: `wrk -t2 -c10 -d15s http://localhost:8000/` (warm) vs `... http://localhost:8001/` (direct) vs `... -H 'Cookie: sessionid=x' http://localhost:8000/` (bypassed)

## What's deliberately demo-grade

- Hard-coded credentials, `ALLOWED_HOSTS = ["*"]`, no TLS — the subject here is the request path, not hardening
- 10s TTL is aggressive microcaching to make expiry observable; real sites tune per-URL
- Session cookie ⇒ full bypass is the blunt-but-safe rule; production systems cache *around* personalization (fragment caching, edge-side includes) to keep logged-in traffic partially cacheable
