from django.urls import path
from . import views

app_name = "tablero"

urlpatterns = [
    path("", views.tablero_home, name="home"),
    path("archivo/", views.archivo, name="archivo"),
    path("admin/nueva/", views.crear, name="crear"),
    path("admin/<int:pk>/editar/", views.editar, name="editar"),
    path("admin/<int:pk>/eliminar/", views.eliminar, name="eliminar"),
]