from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PerfilUsuario


class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [PerfilUsuarioInline]


# Reemplazamos el admin por defecto de User
admin.site.unregister(User)
admin.site.register(User, UserAdmin)