import random
from django.core.management.base import BaseCommand
from demo.models import Sample


CATEGORIES = ["alpha", "beta", "gamma", "delta", "epsilon"]


class Command(BaseCommand):
    """
    seed 100K rows in the database
    """

    help = "Seed 100K rows in database"

    def handle(self, *args, **opts):
        Sample.objects.all().delete()
        batch = [
            Sample(category=random.choice(CATEGORIES), value=random.uniform(0, 1000))
            for _ in range(100000)
        ]

        Sample.objects.bulk_create(batch, batch_size=5000)
        self.stdout.write("Seeded 100K rows")