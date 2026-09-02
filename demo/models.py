from django.db import models


class Sample(models.Model):
    category = models.CharField(max_length=20)
    value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
