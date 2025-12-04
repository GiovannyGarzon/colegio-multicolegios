from django.urls import path
from . import views

app_name = "cartera"

urlpatterns = [
    path("", views.home, name="home"),
    path("anios/", views.anios_list, name="anios"),
    path("anios/nuevo/", views.anio_create, name="anio_create"),
    path("anios/<int:pk>/editar/", views.anio_update, name="anio_update"),
    path("anios/<int:pk>/eliminar/", views.anio_delete, name="anio_delete"),
    path("anios/<int:pk>/activar/", views.anio_set_activo, name="anio_set_activo"),
    path("conceptos/", views.conceptos_list, name="conceptos"),
    path("cuentas/", views.cuentas_list, name="cuentas"),
    path("pagos/", views.pagos_list, name="pagos"),
    path("reportes/", views.reportes_home, name="reportes"),
    path("conceptos/", views.conceptos_list, name="conceptos"),
    path("conceptos/nuevo/", views.concepto_create, name="concepto_create"),
    path("conceptos/<int:pk>/editar/", views.concepto_update, name="concepto_update"),
    path("conceptos/<int:pk>/eliminar/", views.concepto_delete, name="concepto_delete"),
    path("cuentas/", views.cuentas_list, name="cuentas"),
    path("cuentas/nueva/", views.cuenta_create, name="cuenta_create"),
    path("cuentas/<int:pk>/editar/", views.cuenta_update, name="cuenta_update"),
    path("cuentas/<int:pk>/eliminar/", views.cuenta_delete, name="cuenta_delete"),
    path("pagos/", views.pagos_list, name="pagos"),
    path("pagos/nuevo/", views.pago_create, name="pago_create"),
    path("pagos/<int:pk>/editar/", views.pago_update, name="pago_update"),
    path("pagos/<int:pk>/eliminar/", views.pago_delete, name="pago_delete"),
    path("pensiones/selector/", views.cargos_mensuales_selector, name="cargos_mensuales_selector"),
    path("pensiones/planilla/", views.cargos_mensuales_planilla, name="cargos_mensuales_planilla"),
# Hub de reportes
    path("reportes/", views.reportes_home, name="reportes"),
# Reportes individuales
    path("reportes/pagos-por-anio/", views.reporte_pagos_por_anio, name="rep_pagos_anio"),
    path("reportes/pendientes/", views.reporte_pendientes, name="rep_pendientes"),
    path("reportes/medios-pago/", views.reporte_medios_pago, name="rep_medios"),
    path("reportes/morosidad/", views.reporte_morosos, name="rep_morosos"),
]