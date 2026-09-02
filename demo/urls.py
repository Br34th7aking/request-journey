from django.urls import path
from demo import views

urlpatterns = [
    path("", views.dashboard),
    path("me", views.me),
]