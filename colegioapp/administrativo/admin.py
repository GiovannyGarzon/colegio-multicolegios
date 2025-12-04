from django.contrib import admin
from .models import Cargo, Empleado, Proveedor, Contrato


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'identificacion', 'cargo', 'fecha_ingreso', 'salario', 'activo')
    list_filter = ('cargo', 'activo')
    search_fields = ('nombres', 'apellidos', 'identificacion', 'cargo__nombre')
    ordering = ('apellidos',)
    date_hierarchy = 'fecha_ingreso'


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'telefono', 'correo')
    search_fields = ('nombre', 'nit', 'correo')
    ordering = ('nombre',)


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'tipo_contrato', 'fecha_inicio', 'fecha_fin', 'valor')
    list_filter = ('tipo_contrato',)
    search_fields = ('empleado__nombres', 'empleado__apellidos', 'tipo_contrato')
    date_hierarchy = 'fecha_inicio'
    ordering = ('-fecha_inicio',)