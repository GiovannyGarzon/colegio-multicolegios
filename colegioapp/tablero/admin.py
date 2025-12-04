from django.contrib import admin
from .models import Noticia

@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'activo', 'fecha_publicacion', 'publicado_por')
    list_filter  = ('activo', 'fecha_publicacion')
    search_fields = ('titulo', 'resumen', 'cuerpo')
    ordering = ('-fecha_publicacion',)