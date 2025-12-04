from django.urls import path
from . import views

app_name = "administrativo"

urlpatterns = [
    path("", views.home, name="home"),
# Proveedores
    path("proveedores/", views.proveedores_list, name="proveedores"),
    path("proveedores/nuevo/", views.proveedor_create, name="proveedor_create"),
    path("proveedores/<int:pk>/editar/", views.proveedor_update, name="proveedor_update"),
    path("proveedores/<int:pk>/eliminar/", views.proveedor_delete, name="proveedor_delete"),
# Contratos
    path("contratos/", views.contratos_list, name="contratos"),
    path("contratos/nuevo/", views.contrato_create, name="contrato_create"),
    path("contratos/<int:pk>/editar/", views.contrato_update, name="contrato_update"),
    path("contratos/<int:pk>/eliminar/", views.contrato_delete, name="contrato_delete"),
# Cargos.
    path("cargos/", views.cargos_list, name="cargos"),
    path("cargos/nuevo/", views.cargo_create, name="cargo_create"),
    path("cargos/<int:pk>/editar/", views.cargo_update, name="cargo_update"),
    path("cargos/<int:pk>/eliminar/", views.cargo_delete, name="cargo_delete"),
# Empleados
    path("empleados/", views.empleados_list, name="empleados"),
    path("empleados/nuevo/", views.empleado_create, name="empleado_create"),
    path("empleados/<int:pk>/editar/", views.empleado_update, name="empleado_update"),
    path("empleados/<int:pk>/eliminar/", views.empleado_delete, name="empleado_delete"),
# Certificacion
    path("certificaciones/", views.certificaciones_buscar, name="certificaciones"),
    path(
        "certificaciones/<str:tipo>/<int:estudiante_id>/pdf/",
        views.certificado_pdf,
        name="certificado_pdf"
    ),
# Matrículas
    path("matriculas/", views.matriculas_list, name="matriculas"),
    path("matriculas/nuevo/", views.matricula_create, name="matricula_create"),
    path("matriculas/<int:pk>/editar/", views.matricula_update, name="matricula_update"),
    path("matriculas/<int:pk>/eliminar/", views.matricula_delete, name="matricula_delete"),
    path("matriculas/promocionar/", views.matriculas_promocionar, name="matriculas_promocionar"),
]