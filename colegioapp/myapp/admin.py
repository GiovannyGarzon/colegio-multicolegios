from django.contrib import admin
from .models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "domain")
    search_fields = ("name", "domain")

    fieldsets = (
        ("Identidad institucional", {
            "fields": (
                "name",
                "domain",
                "logo",
                "sello",   # 👈 NUEVO CAMPO
                "slogan",
            )
        }),
        ("Colores", {
            "fields": (
                "primary_color",
                "secondary_color",
                "button_color",
                "background_color",
            )
        }),
        ("Contenido Institucional", {
            "fields": (
                "mission",
                "vision",
            )
        }),
        ("Contacto", {
            "fields": (
                "address",
                "phone",
            )
        }),
    )