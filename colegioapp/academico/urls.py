from django.urls import path
from . import views

app_name = "academico"

urlpatterns = [
    # Home / Hub
    path("", views.home, name="home"),
    path("hub/", views.hub_academico, name="hub"),
    path("portal/", views.portal_estudiante, name="portal"),  # ← ESTA LÍNEA
    path("portal/boletin/", views.portal_boletin, name="portal_boletin"),
    path("portal/boletin/pdf/", views.portal_boletin_pdf, name="portal_boletin_pdf"),
    path("observacion/nueva/", views.observacion_nueva, name="observacion_nueva"),
    path("boletines/estudiante/pdf/", views.boletin_estudiante_pdf, name="boletin_estudiante_pdf"),

    # Estudiantes
    path("estudiantes/", views.estudiantes_list, name="estudiantes"),
    path("estudiantes/nuevo/", views.estudiante_create, name="estudiante_create"),
    path("estudiantes/<int:pk>/", views.estudiante_detail, name="estudiante_detail"),
    path("estudiantes/<int:pk>/editar/", views.estudiante_update, name="estudiante_update"),
    path("estudiantes/<int:pk>/eliminar/", views.estudiante_delete, name="estudiante_delete"),

    # Docentes
    path("docentes/", views.docentes_list, name="docentes"),
    path("docentes/nuevo/", views.docente_create, name="docente_create"),
    path("docentes/<int:pk>/", views.docente_detail, name="docente_detail"),
    path("docentes/<int:pk>/editar/", views.docente_update, name="docente_update"),
    path("docentes/<int:pk>/eliminar/", views.docente_delete, name="docente_delete"),

    # Cursos
    path("cursos/", views.cursos_list, name="cursos"),
    path("cursos/nuevo/", views.curso_create, name="curso_create"),
    path("cursos/<int:pk>/editar/", views.curso_edit, name="curso_edit"),
    path("cursos/<int:pk>/eliminar/", views.curso_delete, name="curso_delete"),

    # Asignaturas (Catálogo)
    path("asignaturas/", views.asignaturas_list, name="asignaturas"),
    path("asignaturas/nueva/", views.asignatura_create, name="asignatura_create"),
    path("asignaturas/<int:pk>/editar/", views.asignatura_update, name="asignatura_update"),
    path("asignaturas/<int:pk>/eliminar/", views.asignatura_delete, name="asignatura_delete"),

    # Ofertas de asignaturas
    path("ofertas/", views.ofertas_list, name="ofertas"),
    path("ofertas/nueva/", views.oferta_create, name="oferta_create"),
    path("ofertas/<int:pk>/editar/", views.oferta_update, name="oferta_update"),
    path("ofertas/<int:pk>/eliminar/", views.oferta_delete, name="oferta_delete"),
    path("ofertas/bulk/", views.oferta_bulk_create, name="oferta_bulk_create"),

    # Periodos
    path("periodos/", views.periodos_list, name="periodos"),
    path("periodos/nuevo/", views.periodo_create, name="periodo_create"),
    path("periodos/<int:pk>/editar/", views.periodo_update, name="periodo_update"),
    path("periodos/<int:pk>/eliminar/", views.periodo_delete, name="periodo_delete"),

    # Logros
    path("logros/", views.logros_list, name="logros"),
    path("logros/nuevo/", views.logro_create, name="logro_create"),
    path("logros/<int:pk>/editar/", views.logro_update, name="logro_update"),
    path("logros/<int:pk>/eliminar/", views.logro_delete, name="logro_delete"),

    # Notas
    path("notas/selector/", views.notas_selector, name="notas_selector"),
    path("notas/capturar/", views.notas_capturar, name="notas_capturar"),

    # Boletines
    path("boletines/selector/", views.boletin_selector, name="boletin_selector"),
    path("boletines/generar/", views.boletin_generar, name="boletin_generar"),
    path("boletines/estudiante/", views.boletin_estudiante, name="boletin_estudiante"),

    #Asistencia
    path("asistencia/", views.asistencia_selector, name="asistencia_selector"),
    path("asistencia/tomar/", views.asistencia_tomar, name="asistencia_tomar"),

    #anioelectivo
    path("anios-lectivos/", views.anios_lectivos_list, name="anios_lectivos"),
    path("anios-lectivos/nuevo/", views.anio_lectivo_create, name="anio_lectivo_create"),
    path("anios-lectivos/<int:pk>/editar/", views.anio_lectivo_update, name="anio_lectivo_update"),
    path("anios-lectivos/<int:pk>/eliminar/", views.anio_lectivo_delete, name="anio_lectivo_delete"),
]