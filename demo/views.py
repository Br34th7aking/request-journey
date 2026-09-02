from django.shortcuts import render
from django.db.models import Avg, Count, Max
from django.utils import timezone
from demo.models import Sample


# generic - cacheable
def dashboard(request):
    stats = (
        Sample.objects.values("category")
        .annotate(n=Count("id"), avg=Avg("value"), max=Max("value"))
        .order_by("category")
    )
    randoms = Sample.objects.order_by("?")[:5]

    return render(request, "demo/dashboard.html", {"stats": stats, "randoms": randoms, "rendered_at": timezone.now()})


# user-specific - can not cache
def me(request):
    request.session["visits"] = request.session.get("visits", 0) + 1
    return render(request, "demo/me.html", {"visits": request.session["visits"], "rendered_at": timezone.now()})


