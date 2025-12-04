from django.contrib import admin
from .models import AnioEconomico, ConceptoPago, CuentaPorCobrar, Pago


@admin.register(AnioEconomico)
class AnioEconomicoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('-nombre',)


@admin.register(ConceptoPago)
class ConceptoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'anio', 'valor', 'recurrente', 'activo')
    list_filter = ('anio', 'activo', 'recurrente')
    search_fields = ('nombre', 'anio__nombre')
    ordering = ('anio', 'nombre')


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = (
        'estudiante',
        'concepto',
        'fecha_generacion',
        'fecha_vencimiento',
        'valor_total',
        'saldo_pendiente',
        'pagada',
    )
    list_filter = ('pagada', 'concepto__anio')
    search_fields = (
        'estudiante__nombres',
        'estudiante__apellidos',
        'concepto__nombre',
        'concepto__anio__nombre',
    )
    date_hierarchy = 'fecha_generacion'
    ordering = ('-fecha_generacion',)
    readonly_fields = ('fecha_generacion',)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('cuenta', 'fecha_pago', 'valor_pagado', 'medio_pago')
    list_filter = ('medio_pago', 'fecha_pago')
    search_fields = (
        'cuenta__estudiante__nombres',
        'cuenta__estudiante__apellidos',
        'cuenta__concepto__nombre',
    )
    date_hierarchy = 'fecha_pago'
    ordering = ('-fecha_pago',)
    readonly_fields = ('fecha_pago',)
