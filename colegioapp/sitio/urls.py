from django.urls import path
from . import views

app_name = "sitio"

urlpatterns = [
    path("", views.home, name="home_publico"),
    path("nosotros/", views.nosotros, name="nosotros"),
    path("admisiones/", views.admisiones, name="admisiones"),
    path("noticias/", views.noticias, name="noticias"),
    path("contacto/", views.contacto, name="contacto"),
]