from decimal import Decimal
from django.contrib import admin
from django.db.models import Count
from .models import (
    Curso, Docente, Estudiante,
    AnioLectivo, Periodo,
    AsignaturaCatalogo, AsignaturaOferta,
    Logro, CalificacionLogro, Observador, ObservacionBoletin, PaseLista, AsistenciaDetalle, Matricula, BloqueHorario
)

@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ("estudiante", "anio", "curso", "activo", "fecha_matricula")
    list_filter = ("anio", "curso", "activo")
    search_fields = ("estudiante__nombres", "estudiante__apellidos", "estudiante__identificacion")

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('grado', 'nombre', 'jornada')
    search_fields = ('nombre', 'grado', 'jornada')
    list_filter = ('grado', 'jornada')
    ordering = ('grado', 'nombre')
    list_per_page = 25


@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ('apellidos', 'nombres', 'identificacion', 'curso_asignado')
    search_fields = ('nombres', 'apellidos', 'identificacion')
    list_filter = ('curso_asignado',)
    ordering = ('apellidos', 'nombres')
    autocomplete_fields = ('curso_asignado',)
    list_per_page = 25


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ('apellidos', 'nombres', 'identificacion', 'curso', 'acudiente', 'get_user')
    search_fields = ('nombres', 'apellidos', 'identificacion', 'acudiente', 'correo', 'telefono', 'user__username')
    list_filter = ('curso',)
    ordering = ('apellidos', 'nombres')
    autocomplete_fields = ('curso',)
    list_per_page = 25

    @admin.display(description="Usuario")
    def get_user(self, obj):
        return obj.user.username if obj.user else "—"


# =========================
#   AÑO LECTIVO / PERIODOS
# =========================

class PeriodoInline(admin.TabularInline):
    model = Periodo
    extra = 0
    fields = ('numero', 'nombre', 'peso')
    ordering = ('numero',)


@admin.register(AnioLectivo)
class AnioLectivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo', 'total_periodos')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    ordering = ('-activo', '-nombre')
    inlines = [PeriodoInline]
    list_per_page = 25
    actions = ['generar_periodos_1_4']

    @admin.display(description="Periodos")
    def total_periodos(self, obj):
        return obj.periodos.count()

    @admin.action(description="Generar periodos 1..4 (25%% c/u) si no existen")
    def generar_periodos_1_4(self, request, queryset):
        creados = 0
        for anio in queryset:
            for i in range(1, 5):
                if not Periodo.objects.filter(anio=anio, numero=i).exists():
                    Periodo.objects.create(
                        anio=anio,
                        numero=i,
                        nombre=f"Periodo {i}",
                        peso=Decimal("25.00")
                    )
                    creados += 1
        self.message_user(request, f"Se generaron {creados} periodos nuevos.")


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('anio', 'numero', 'nombre', 'peso')
    list_filter = ('anio',)
    search_fields = ('nombre', 'anio__nombre')
    ordering = ('anio__nombre', 'numero')
    list_per_page = 25


# =========================
#   ASIGNATURAS (CATÁLOGO / OFERTAS)
# =========================

@admin.register(AsignaturaCatalogo)
class AsignaturaCatalogoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'area', 'ofertas_count')
    search_fields = ('nombre', 'area')
    ordering = ('nombre',)
    list_per_page = 25

    @admin.display(description="Ofertas")
    def ofertas_count(self, obj):
        return obj.ofertas.count()


class LogroInline(admin.TabularInline):
    model = Logro
    extra = 0
    fields = ('periodo', 'titulo', 'peso')
    autocomplete_fields = ('periodo',)
    ordering = ('periodo__numero', 'titulo')
    show_change_link = True


@admin.register(AsignaturaOferta)
class AsignaturaOfertaAdmin(admin.ModelAdmin):
    list_display = ('anio', 'curso', 'asignatura', 'docente', 'intensidad_horaria', 'logros_count')
    list_filter = ('anio', 'curso', 'asignatura', 'docente')
    search_fields = ('anio__nombre', 'curso__nombre', 'curso__grado', 'asignatura__nombre', 'docente__nombres', 'docente__apellidos')
    ordering = ('anio__nombre', 'curso__grado', 'curso__nombre', 'asignatura__nombre')
    autocomplete_fields = ('anio', 'curso', 'asignatura', 'docente')
    inlines = [LogroInline]
    list_per_page = 25

    @admin.display(description="Logros")
    def logros_count(self, obj):
        return obj.logros.count()


@admin.register(Logro)
class LogroAdmin(admin.ModelAdmin):
    list_display = ('oferta', 'periodo', 'titulo', 'peso')
    list_filter = ('oferta__anio', 'oferta__curso', 'oferta__asignatura', 'periodo')
    search_fields = ('titulo', 'descripcion', 'oferta__asignatura__nombre', 'oferta__curso__nombre', 'periodo__nombre', 'oferta__anio__nombre')
    ordering = ('oferta__anio__nombre', 'oferta__curso__grado', 'oferta__asignatura__nombre', 'periodo__numero', 'titulo')
    autocomplete_fields = ('oferta', 'periodo')
    list_per_page = 25


# =========================
#   CALIFICACIONES (POR LOGRO)
# =========================

@admin.register(CalificacionLogro)
class CalificacionLogroAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'get_anio', 'get_curso', 'get_asignatura', 'get_periodo', 'logro', 'nota', 'fecha_registro')
    list_filter = (
        'logro__periodo__anio',
        'logro__periodo',
        'logro__oferta__curso',
        'logro__oferta__asignatura',
    )
    search_fields = (
        'estudiante__nombres', 'estudiante__apellidos', 'estudiante__identificacion',
        'logro__titulo', 'logro__oferta__asignatura__nombre',
    )
    ordering = ('-fecha_registro',)
    autocomplete_fields = ('estudiante', 'logro')
    list_per_page = 50

    @admin.display(description="Año")
    def get_anio(self, obj):
        return obj.logro.periodo.anio

    @admin.display(description="Curso")
    def get_curso(self, obj):
        return obj.logro.oferta.curso

    @admin.display(description="Asignatura")
    def get_asignatura(self, obj):
        return obj.logro.oferta.asignatura

    @admin.display(description="Periodo")
    def get_periodo(self, obj):
        return obj.logro.periodo

@admin.register(ObservacionBoletin)
class ObservacionBoletinAdmin(admin.ModelAdmin):
    list_display = (
        "estudiante",
        "periodo",
        "docente",
        "fecha_actualizacion",
        "texto_corto",
    )
    list_filter = (
        "periodo__anio",
        "periodo",
        "docente",
        "estudiante__curso",
    )
    search_fields = (
        "estudiante__nombres",
        "estudiante__apellidos",
        "estudiante__identificacion",
        "texto",
    )
    autocomplete_fields = ("estudiante", "periodo", "docente")
    date_hierarchy = "fecha_actualizacion"
    ordering = ("-fecha_actualizacion",)

    def texto_corto(self, obj):
        if len(obj.texto) > 80:
            return obj.texto[:80] + "..."
        return obj.texto

    texto_corto.short_description = "Observación"

class AsistenciaDetalleInline(admin.TabularInline):
    model = AsistenciaDetalle
    extra = 0

@admin.register(PaseLista)
class PaseListaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "curso", "anio", "periodo", "docente")
    list_filter = ("anio", "periodo", "curso")
    inlines = [AsistenciaDetalleInline]

@admin.register(BloqueHorario)
class BloqueHorarioAdmin(admin.ModelAdmin):
    list_display = (
        "anio",
        "curso",
        "get_dia",
        "hora_inicio",
        "hora_fin",
        "get_tipo",
        "get_asignatura",
        "get_docente",
    )
    list_filter = (
        "anio",
        "curso",
        "dia_semana",
        "es_receso",
    )
    search_fields = (
        "curso__nombre",
        "curso__grado",
        "oferta__asignatura__nombre",
        "oferta__docente__nombres",
        "oferta__docente__apellidos",
        "descripcion",
    )
    ordering = ("anio__nombre", "curso__grado", "curso__nombre", "dia_semana", "hora_inicio")
    autocomplete_fields = ("anio", "curso", "oferta")
    list_per_page = 50

    @admin.display(description="Día")
    def get_dia(self, obj):
        return obj.get_dia_semana_display()

    @admin.display(description="Tipo")
    def get_tipo(self, obj):
        return "Receso" if obj.es_receso else "Clase"

    @admin.display(description="Asignatura")
    def get_asignatura(self, obj):
        if obj.es_receso:
            return "—"
        return obj.oferta.asignatura if obj.oferta else "—"

    @admin.display(description="Docente")
    def get_docente(self, obj):
        if obj.es_receso or not obj.oferta or not obj.oferta.docente:
            return "—"
        d = obj.oferta.docente
        return f"{d.apellidos} {d.nombres}"

admin.site.register(Observador)
