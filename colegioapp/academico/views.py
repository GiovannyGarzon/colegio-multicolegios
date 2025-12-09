from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from urllib.parse import urlencode
from django.db.models import Q, Prefetch, Sum, Avg, Count
from django.urls import reverse
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from django.templatetags.static import static
from django.contrib.auth.models import User, Group
from django.db import transaction
from academico.utils_notas import recalcular_nota_logro_desde_actividades
from django.conf import settings
import os
from cartera.utils import estudiante_tiene_deuda_bloqueante, resumen_cartera_para_boletin
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from datetime import date
from .models import (
    Estudiante, Curso, Docente, AnioLectivo, Periodo,
    Logro, AsignaturaOferta, AsignaturaCatalogo, CalificacionLogro, Observador, ObservacionBoletin, PaseLista,
    AsistenciaDetalle, BloqueHorario, Actividad, CalificacionActividad, SaberSer
)
from .forms import (
    EstudianteForm, DocenteForm, CursoForm,
    AsignaturaCatalogoForm, AsignaturaOfertaForm, OfertaBulkForm,
    PeriodoForm, LogroForm, AnioLectivoForm
)
from django.contrib.auth.decorators import login_required, user_passes_test
from academico.utils import ranking_curso_periodo, ranking_curso_anual, _promedio_asignatura_periodo
from collections import defaultdict
import io
import zipfile
from weasyprint import HTML

from cartera.models import AnioEconomico

SABER_SER_PESO = Decimal("0.10")  # 10%
LOGROS_PESO    = Decimal("0.90")  # 90%

@transaction.atomic
def crear_usuario_estudiante(estudiante):
    """
    Crea un User y lo vincula al Estudiante si aún no tiene uno.
    Devuelve (user, password_clara).
    """
    if estudiante.user:   # ya tiene usuario
        return estudiante.user, None

    username = f"est{estudiante.identificacion}"
    email = estudiante.correo or ""
    password = User.objects.make_random_password()

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=estudiante.nombres,
        last_name=estudiante.apellidos,
    )

    # Añadir al grupo "Estudiante" si existe
    try:
        g = Group.objects.get(name="Estudiante")
        user.groups.add(g)
    except Group.DoesNotExist:
        pass

    estudiante.user = user
    estudiante.save(update_fields=["user"])

    return user, password


@transaction.atomic
def crear_usuario_docente(docente):
    """
    Crea un User y lo vincula al Docente si aún no tiene uno.
    Devuelve (user, password_clara).
    """
    if docente.usuario:   # ya tiene usuario
        return docente.usuario, None

    username = f"doc{docente.identificacion}"
    email = docente.correo or ""
    password = User.objects.make_random_password()

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=docente.nombres,
        last_name=docente.apellidos,
    )

    # Añadir al grupo "Docente" si existe
    try:
        g = Group.objects.get(name="Docente")
        user.groups.add(g)
    except Group.DoesNotExist:
        pass

    docente.usuario = user
    docente.save(update_fields=["usuario"])

    return user, password

@login_required
def portal_boletin_pdf(request):
    # Solo el estudiante dueño
    est = Estudiante.objects.select_related("curso").filter(user=request.user).first()
    if not est:
        messages.error(request, "Tu usuario no está vinculado a un estudiante.")
        return redirect("academico:home")

    if estudiante_tiene_deuda_bloqueante(est):
        messages.error(
            request,
            "Tienes pagos pendientes vencidos. "
            "Por favor acércate a cartera; mientras tanto no puedes descargar tu boletín en PDF."
        )
        return redirect("academico:portal")

    anio = AnioLectivo.objects.filter(activo=True).first()
    if not anio:
        messages.error(request, "No hay año lectivo activo.")
        return redirect("academico:portal")

    periodo_id = request.GET.get("periodo")
    if not periodo_id:
        messages.info(request, "Selecciona un período para descargar el PDF.")
        return redirect("academico:portal")
    periodo = get_object_or_404(Periodo, pk=periodo_id, anio=anio)

    # Calificaciones SOLO de este estudiante en ese periodo
    calificaciones = (
        CalificacionLogro.objects
        .filter(estudiante=est, logro__periodo=periodo)
        .select_related("logro__oferta__asignatura", "logro")
        .order_by("logro__oferta__asignatura__nombre", "logro__titulo")
    )

    # === Generar PDF ===
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="boletin_{est.apellidos}_{est.nombres}_P{periodo.numero}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>Estudiante:</b> {est.nombres} {est.apellidos}", styles["Normal"]))
    story.append(Paragraph(f"<b>Curso:</b> {est.curso}", styles["Normal"]))
    story.append(Paragraph(f"<b>Periodo:</b> {periodo.nombre}", styles["Normal"]))
    story.append(Spacer(1, 10))

    data = [["Asignatura", "Logro", "Nota", "Peso %"]]
    for c in calificaciones:
        data.append([
            c.logro.oferta.asignatura.nombre,
            c.logro.titulo,
            f"{(c.nota or 0):.2f}",
            f"{c.logro.peso}%",
        ])
    if len(data) == 1:
        data.append(["Sin calificaciones registradas", "", "", ""])

    table = Table(data, colWidths=[130, 250, 60, 60])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("ALIGN", (2, 1), (3, -1), "CENTER"),
    ]))
    story.append(table)
    doc.build(story)
    return response

@login_required
def portal_boletin(request):
    # Debe ser estudiante
    est = Estudiante.objects.select_related("curso").filter(user=request.user).first()
    if not est:
        messages.error(request, "Tu usuario no está vinculado a un estudiante.")
        return redirect("academico:home")

    if estudiante_tiene_deuda_bloqueante(est):
        messages.error(
            request,
            "Tienes pagos pendientes vencidos. "
            "Por favor acércate a cartera; mientras tanto no puedes ver tu boletín."
        )
        return redirect("academico:portal")

    anio = AnioLectivo.objects.filter(activo=True).first()
    if not anio:
        messages.error(request, "No hay año lectivo activo.")
        return redirect("academico:portal")

    periodo_id = request.GET.get("periodo")
    if not periodo_id:
        messages.info(request, "Selecciona un período para ver tu boletín.")
        return redirect("academico:portal")

    periodo = get_object_or_404(Periodo, pk=periodo_id, anio=anio)

    # Ofertas (asignaturas) del curso del estudiante en el año activo
    ofertas = (
        AsignaturaOferta.objects
        .select_related("asignatura", "docente")
        .filter(anio=anio, curso=est.curso)
        .order_by("asignatura__area", "asignatura__nombre")
    )

    # ============================
    #   RESUMEN DE TRES TRIMESTRES
    # ============================
    periodos_anio = list(
        Periodo.objects.filter(anio=anio).order_by("numero")[:3]
    )

    resumen_asignaturas = []

    for of in ofertas:
        fila_resumen = {
            "asignatura": of.asignatura.nombre,
        }

        proms_validos = []

        # p1, p2, p3 si existen
        for idx, per in enumerate(periodos_anio, start=1):
            prom_p = _promedio_asignatura_periodo(est, of, per)
            clave = f"p{idx}"
            fila_resumen[clave] = prom_p
            if prom_p is not None:
                proms_validos.append(prom_p)

        # Promedio final
        prom_final = None
        if proms_validos:
            prom_final = (sum(proms_validos) / len(proms_validos)).quantize(Decimal("0.01"))

        fila_resumen["prom_final"] = prom_final
        fila_resumen["letra_final"] = _concepto_letra(prom_final)

        resumen_asignaturas.append(fila_resumen)

    # Promedios globales por trimestre
    promedios_trimestre = []
    for per in periodos_anio:
        notas = []
        for of in ofertas:
            p = _promedio_asignatura_periodo(est, of, per)
            if p is not None:
                notas.append(p)
        prom = None
        if notas:
            prom = (sum(notas) / len(notas)).quantize(Decimal("0.01"))
        promedios_trimestre.append(prom)

    # Promedio anual
    notas_validas = [p for p in promedios_trimestre if p is not None]
    promedio_anual = None
    if notas_validas:
        promedio_anual = (sum(notas_validas) / len(notas_validas)).quantize(Decimal("0.01"))

    # ============================
    #   AGRUPAR POR ÁREA (lo que ya tenías)
    # ============================
    from collections import defaultdict
    areas_dict = defaultdict(list)

    for of in ofertas:
        area_nombre = of.asignatura.area or "Otras áreas"

        logros = Logro.objects.filter(oferta=of, periodo=periodo).order_by("titulo")
        cals = (
            CalificacionLogro.objects
            .filter(estudiante=est, logro__in=logros)
            .select_related("logro")
        )

        detalle = []
        suma_pesada = Decimal("0")
        suma_pesos = Decimal("0")
        notas_por_logro = {c.logro_id: c.nota for c in cals}

        for lg in logros:
            nota = notas_por_logro.get(lg.id)
            detalle.append({"titulo": lg.titulo, "peso": lg.peso, "nota": nota})
            if nota is not None:
                suma_pesada += Decimal(nota) * (lg.peso / Decimal("100"))
                suma_pesos += (lg.peso / Decimal("100"))

        promedio = None
        if suma_pesos > 0:
            promedio = (suma_pesada / suma_pesos).quantize(Decimal("0.01"))

        fila = {
            "asignatura": of.asignatura.nombre,
            "docente": f"{of.docente.apellidos} {of.docente.nombres}" if of.docente else "—",
            "promedio": promedio,
            "letra": _concepto_letra(promedio),
            "detalle": detalle,
        }

        areas_dict[area_nombre].append(fila)

    areas = [
        {"nombre": nombre, "filas": filas}
        for nombre, filas in areas_dict.items()
    ]
    areas.sort(key=lambda a: a["nombre"])

    # === Observación general ===
    obs_general = ObservacionBoletin.objects.filter(
        estudiante=est, periodo=periodo
    ).first()

    # ============================
    #   ENVIAR TODO AL TEMPLATE
    # ============================
    ctx = {
        "anio": anio,
        "curso": est.curso,
        "periodo": periodo,
        "estudiante": est,
        "areas": areas,
        "obs_general": obs_general,

        # NUEVO 👇👇👇
        "resumen_asignaturas": resumen_asignaturas,
        "promedios_trimestre": promedios_trimestre,
        "promedio_anual": promedio_anual,
    }

    return render(request, "academico/boletin_estudiante.html", ctx)

def _es_estudiante(u):
    return u.is_authenticated and u.groups.filter(name="Estudiante").exists()

def _puede_gestionar(u):
    # staff, superuser o docente
    return u.is_authenticated and (u.is_staff or u.is_superuser or u.groups.filter(name="Docente").exists())

def requiere_gestion(view_func):
    """Decorator: requiere ser staff/superuser/docente; si es estudiante, va al portal."""
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not _puede_gestionar(request.user):
            # Usuario autenticado pero sin permisos de gestión -> al portal de estudiante
            if _es_estudiante(request.user):
                return redirect("academico:portal")
            # Otro usuario autenticado sin permisos -> home académico
            return redirect("academico:home")
        return view_func(request, *args, **kwargs)
    return _wrapped

# ----------------- Portal estudiante -----------------

@login_required
def portal_estudiante(request):
    # 1. Estudiante vinculado al usuario
    est = (
        Estudiante.objects
        .select_related("curso")
        .filter(user=request.user)
        .first()
    )
    if not est:
        messages.error(request, "Tu usuario no está vinculado a un estudiante.")
        return redirect("academico:home")

    # 2. Año lectivo activo
    anio = AnioLectivo.objects.filter(activo=True).first()

    # 3. Observaciones recientes (si el modelo las tiene)
    observaciones = []
    if hasattr(est, "observaciones"):
        observaciones = est.observaciones.all().order_by("-fecha")[:5]

    # 4. Promedios por asignatura
    promedios = []
    if anio:
        ofertas = (
            AsignaturaOferta.objects
                .select_related("asignatura")
                .filter(anio=anio, curso=est.curso)
        )
        for of in ofertas:
            qs = CalificacionLogro.objects.filter(
                estudiante=est,
                logro__oferta=of,  # 👈 usamos el FK a través de Logro
            )
            if qs.exists():
                promedios.append({
                    "asignatura": of.asignatura.nombre,
                    "promedio": qs.aggregate(p=Avg("nota"))["p"],
                })

    # 5. Períodos del año
    periodos = Periodo.objects.filter(anio=anio).order_by("numero") if anio else []

    # 6. Resumen de asistencia del año
    fallas_anio = 0
    tardanzas_anio = 0
    if anio and est.curso:
        pases = PaseLista.objects.filter(
            anio=anio,
            curso=est.curso,
            periodo__in=periodos
        )

        fallas_anio = AsistenciaDetalle.objects.filter(
            pase__in=pases,
            estudiante=est,
            estado=AsistenciaDetalle.AUSENTE
        ).count()

        tardanzas_anio = AsistenciaDetalle.objects.filter(
            pase__in=pases,
            estudiante=est,
            estado=AsistenciaDetalle.TARDANZA
        ).count()

        # ===============================
        #  Horario compacto por nivel
        # ===============================
        # Puedes cambiar estos textos/horas cuando quieras
        horarios_nivel = {
            "preescolar": {
                "titulo": "Preescolar",
                "inicio": "6:45 a. m.",
                "fin": "12:45 p. m.",
            },
            "primaria": {
                "titulo": "Primaria",
                "inicio": "6:45 a. m.",
                "fin": "2:00 p. m.",
            },
            "bachillerato": {
                "titulo": "Bachillerato",
                "inicio": "6:45 a. m.",
                "fin": "2:00 p. m.",
            },
        }

        nivel_horario = None  # preescolar / primaria / bachillerato

        if est.curso:
            grado = str(est.curso.grado).upper()

            # 👇 Ajusta esta lista según cómo tengas guardado el grado
            if grado in ["JARDIN", "JARDÍN", "PREJARDIN", "PREJARDÍN", "TRANSICION", "TRANSICIÓN"]:
                nivel_horario = "preescolar"
            elif grado in ["1", "01", "PRIMERO", "2", "SEGUNDO", "3", "TERCERO", "4", "CUARTO", "5", "QUINTO"]:
                nivel_horario = "primaria"
            else:
                nivel_horario = "bachillerato"

    ctx = {
        "est": est,
        "anio": anio,
        "observaciones": observaciones,
        "promedios": promedios,
        "nav_active": "academico",
        "periodos": periodos,
        "fallas_anio": fallas_anio,
        "tardanzas_anio": tardanzas_anio,
        "horarios_nivel": horarios_nivel,
        "nivel_horario": nivel_horario,
    }

    return render(request, "portal/inicio.html", ctx)

# ----------------- Rutas generales / home -----------------

@login_required
def home(request):
    # Si es estudiante → enviar al portal
    if _es_estudiante(request.user):
        return redirect("academico:portal")

    # Si NO es estudiante → enviar datos y permitir ver el módulo académico
    return render(request, "academico/homeacademico.html", {
        "nav_active": "academico",
        "es_directivo": es_directivo(request.user),  # 👈 AÑADIDO
    })

@login_required
def hub_academico(request):
    # Estudiante no puede ver el hub: lo mandamos al portal
    if _es_estudiante(request.user):
        return redirect("academico:portal")
    return render(request, "academico/hub_academico.html", {"nav_active": "academico"})

# ----------------- Estudiantes (gestión) -----------------

@requiere_gestion
def estudiantes_list(request):
    q = (request.GET.get('q') or '').strip()
    curso_id = (request.GET.get('curso') or '').strip()

    qs = (Estudiante.objects
          .select_related('curso')
          .order_by('apellidos', 'nombres'))

    if q:
        qs = qs.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(identificacion__icontains=q)
        )
    if curso_id:
        qs = qs.filter(curso_id=curso_id)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    cursos = Curso.objects.all().order_by('grado', 'nombre')

    base_params = {}
    if q:
        base_params['q'] = q
    if curso_id:
        base_params['curso'] = curso_id
    querystring = urlencode(base_params)

    context = {
        "page_obj": page_obj,
        "cursos": cursos,
        "q": q,
        "curso_selected": curso_id,
        "querystring": querystring,
        "nav_active": "academico",
    }
    return render(request, "academico/estudiantes.html", context)

@requiere_gestion
def estudiante_create(request):
    if request.method == "POST":
        form = EstudianteForm(request.POST, request.FILES)
        if form.is_valid():
            est = form.save()  # creamos el Estudiante

            user, pwd = crear_usuario_estudiante(est)

            msg = "Estudiante creado correctamente."
            if pwd:
                msg += f" Usuario: {user.username} - Contraseña: {pwd}"
            messages.success(request, msg)

            return redirect(reverse("academico:estudiantes"))
    else:
        form = EstudianteForm()
    return render(
        request,
        "academico/estudiante_form.html",
        {"form": form, "title": "Nuevo estudiante", "nav_active": "academico"}
    )


@requiere_gestion
def estudiante_update(request, pk):
    est = get_object_or_404(Estudiante, pk=pk)
    if request.method == "POST":
        form = EstudianteForm(request.POST, request.FILES, instance=est)  # 👈 aquí
        if form.is_valid():
            form.save()
            messages.success(request, "Estudiante actualizado correctamente.")
            return redirect(reverse("academico:estudiantes"))
    else:
        form = EstudianteForm(instance=est)

    return render(
        request,
        "academico/estudiante_form.html",
        {
            "form": form,
            "title": f"Editar estudiante: {est.apellidos} {est.nombres}",
            "nav_active": "academico",
        }
    )

@requiere_gestion
def estudiante_detail(request, pk):
    est = get_object_or_404(Estudiante, pk=pk)
    return render(request, "academico/estudiante_detail.html", {"e": est, "nav_active": "academico"})

@requiere_gestion
def estudiante_delete(request, pk):
    est = get_object_or_404(Estudiante, pk=pk)
    if request.method == "POST":
        est.delete()
        messages.success(request, "Estudiante eliminado.")
        return redirect(reverse("academico:estudiantes"))
    return render(request, "academico/estudiante_confirm_delete.html", {"e": est, "nav_active": "academico"})

# ----------------- Docentes (gestión) -----------------

@requiere_gestion
def docentes_list(request):
    q = (request.GET.get('q') or '').strip()
    curso_id = (request.GET.get('curso') or '').strip()

    qs = (Docente.objects
          .select_related('curso_asignado')
          .order_by('apellidos', 'nombres'))

    if q:
        qs = qs.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(identificacion__icontains=q) |
            Q(correo__icontains=q) |
            Q(telefono__icontains=q)
        )
    if curso_id:
        qs = qs.filter(curso_asignado_id=curso_id)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    cursos = Curso.objects.all().order_by('grado', 'nombre')

    base_params = {}
    if q:
        base_params['q'] = q
    if curso_id:
        base_params['curso'] = curso_id
    querystring = urlencode(base_params)

    ctx = {
        "page_obj": page_obj,
        "cursos": cursos,
        "q": q,
        "curso_selected": curso_id,
        "querystring": querystring,
        "nav_active": "docentes",
    }
    return render(request, "academico/docentes.html", ctx)

@requiere_gestion
def docente_create(request):
    if request.method == "POST":
        form = DocenteForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.save()
            user, pwd = crear_usuario_docente(d)

            msg = "Docente creado correctamente."
            if pwd:
                msg += f" Usuario: {user.username} - Contraseña: {pwd}"
            messages.success(request, msg)

            return redirect(reverse("academico:docentes"))
    else:
        form = DocenteForm()
    return render(
        request,
        "academico/docente_form.html",
        {"form": form, "title": "Nuevo docente", "nav_active": "academico"}
    )

@requiere_gestion
def docente_update(request, pk):
    d = get_object_or_404(Docente, pk=pk)
    if request.method == "POST":
        form = DocenteForm(request.POST, request.FILES, instance=d)
        if form.is_valid():
            form.save()
            messages.success(request, "Docente actualizado correctamente.")
            return redirect(reverse("academico:docentes"))
    else:
        form = DocenteForm(instance=d)
    return render(request, "academico/docente_form.html", {"form": form, "title": f"Editar docente: {d.apellidos} {d.nombres}", "nav_active": "academico"})

@requiere_gestion
def docente_detail(request, pk):
    d = get_object_or_404(Docente, pk=pk)
    return render(request, "academico/docente_detail.html", {"d": d, "nav_active": "academico"})

@requiere_gestion
def docente_delete(request, pk):
    d = get_object_or_404(Docente, pk=pk)
    if request.method == "POST":
        d.delete()
        messages.success(request, "Docente eliminado.")
        return redirect(reverse("academico:docentes"))
    return render(request, "academico/docente_confirm_delete.html", {"d": d, "nav_active": "academico"})

# ----------------- Cursos (gestión) -----------------

@requiere_gestion
def cursos_list(request):
    q = (request.GET.get('q') or '').strip()

    qs = (Curso.objects
          .all()
          .order_by('grado', 'nombre')
          .prefetch_related(
              Prefetch('docente_set', queryset=Docente.objects.order_by('apellidos'))
          ))

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(grado__icontains=q) |
            Q(jornada__icontains=q)
        )

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    ctx = {"page_obj": page_obj, "q": q, "nav_active": "cursos"}
    return render(request, "academico/cursos.html", ctx)

@requiere_gestion
def curso_create(request):
    if request.method == "POST":
        form = CursoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("academico:cursos")
    else:
        form = CursoForm()
    return render(request, "academico/curso_form.html", {"form": form, "nav_active": "academico"})

@requiere_gestion
def curso_edit(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    if request.method == "POST":
        form = CursoForm(request.POST, instance=curso)
        if form.is_valid():
            form.save()
            return redirect("academico:cursos")
    else:
        form = CursoForm(instance=curso)
    return render(request, "academico/curso_form.html", {"form": form, "edit_mode": True, "nav_active": "academico"})

@requiere_gestion
def curso_delete(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    if request.method == "POST":
        curso.delete()
        return redirect("academico:cursos")
    return render(request, "academico/curso_confirm_delete.html", {"curso": curso, "nav_active": "academico"})

# ----------------- Asignaturas (catálogo, gestión) -----------------

@requiere_gestion
def asignaturas_list(request):
    q = (request.GET.get("q") or "").strip()
    asignaturas = AsignaturaCatalogo.objects.all().order_by("nombre")
    if q:
        asignaturas = asignaturas.filter(Q(nombre__icontains=q) | Q(area__icontains=q))

    paginator = Paginator(asignaturas, 10)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop("page", None)
    querystring = urlencode(query_params)

    return render(request, "academico/asignaturas.html", {
        "page_obj": page_obj,
        "q": q,
        "querystring": querystring,
        "nav_active": "academico",
    })

@requiere_gestion
def asignatura_create(request):
    if request.method == "POST":
        form = AsignaturaCatalogoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("academico:asignaturas")
    else:
        form = AsignaturaCatalogoForm()
    return render(request, "academico/asignatura_form.html", {"form": form, "edit_mode": False, "nav_active": "academico"})

@requiere_gestion
def asignatura_update(request, pk):
    obj = get_object_or_404(AsignaturaCatalogo, pk=pk)
    if request.method == "POST":
        form = AsignaturaCatalogoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("academico:asignaturas")
    else:
        form = AsignaturaCatalogoForm(instance=obj)
    return render(request, "academico/asignatura_form.html", {"form": form, "edit_mode": True, "obj": obj, "nav_active": "academico"})

@requiere_gestion
def asignatura_delete(request, pk):
    obj = get_object_or_404(AsignaturaCatalogo, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("academico:asignaturas")
    return render(request, "academico/asignatura_confirm_delete.html", {"obj": obj, "nav_active": "academico"})

# ----------------- Ofertas (gestión) -----------------

@requiere_gestion
def ofertas_list(request):
    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio") or ""
    curso_id = request.GET.get("curso") or ""
    asig_id = request.GET.get("asignatura") or ""
    docente_id = request.GET.get("docente") or ""

    ofertas = AsignaturaOferta.objects.select_related("anio", "curso", "asignatura", "docente").all()

    if q:
        ofertas = ofertas.filter(
            Q(curso__nombre__icontains=q) |
            Q(curso__grado__icontains=q) |
            Q(asignatura__nombre__icontains=q) |
            Q(docente__nombres__icontains=q) |
            Q(docente__apellidos__icontains=q) |
            Q(anio__nombre__icontains=q)
        )
    if anio_id:
        ofertas = ofertas.filter(anio_id=anio_id)
    if curso_id:
        ofertas = ofertas.filter(curso_id=curso_id)
    if asig_id:
        ofertas = ofertas.filter(asignatura_id=asig_id)
    if docente_id:
        ofertas = ofertas.filter(docente_id=docente_id)

    ofertas = ofertas.order_by("anio__nombre", "curso__grado", "curso__nombre", "asignatura__nombre")

    paginator = Paginator(ofertas, 12)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop("page", None)
    querystring = urlencode(params)

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "anio_selected": anio_id,
        "curso_selected": curso_id,
        "asig_selected": asig_id,
        "docente_selected": docente_id,
        "anios": AnioLectivo.objects.all().order_by("-activo", "-nombre"),
        "cursos": Curso.objects.all().order_by("grado", "nombre"),
        "asignaturas": AsignaturaCatalogo.objects.all().order_by("nombre"),
        "docentes": Docente.objects.all().order_by("apellidos", "nombres"),
        "querystring": querystring,
        "nav_active": "academico",
    }
    return render(request, "academico/ofertas.html", ctx)

@requiere_gestion
def oferta_create(request):
    if request.method == "POST":
        form = AsignaturaOfertaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Oferta creada correctamente.")
            return redirect("academico:ofertas")
    else:
        form = AsignaturaOfertaForm()
    return render(request, "academico/oferta_form.html", {"form": form, "edit_mode": False, "nav_active": "academico"})

@requiere_gestion
def oferta_update(request, pk):
    obj = get_object_or_404(AsignaturaOferta, pk=pk)
    if request.method == "POST":
        form = AsignaturaOfertaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Oferta actualizada.")
            return redirect("academico:ofertas")
    else:
        form = AsignaturaOfertaForm(instance=obj)
    return render(request, "academico/oferta_form.html", {"form": form, "edit_mode": True, "obj": obj, "nav_active": "academico"})

@requiere_gestion
def oferta_delete(request, pk):
    obj = get_object_or_404(AsignaturaOferta, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Oferta eliminada.")
        return redirect("academico:ofertas")
    return render(request, "academico/oferta_confirm_delete.html", {"obj": obj, "nav_active": "academico"})

@requiere_gestion
def oferta_bulk_create(request):
    if request.method == "POST":
        form = OfertaBulkForm(request.POST)
        if form.is_valid():
            anio = form.cleaned_data["anio"]
            asignatura = form.cleaned_data["asignatura"]
            cursos = form.cleaned_data["cursos"]
            docente = form.cleaned_data["docente"]
            intensidad = form.cleaned_data["intensidad_horaria"] or 0

            creadas = 0
            duplicadas = 0
            for curso in cursos:
                exists = AsignaturaOferta.objects.filter(
                    anio=anio, curso=curso, asignatura=asignatura
                ).exists()
                if exists:
                    duplicadas += 1
                    continue
                AsignaturaOferta.objects.create(
                    anio=anio, curso=curso, asignatura=asignatura,
                    docente=docente, intensidad_horaria=intensidad
                )
                creadas += 1

            if creadas:
                messages.success(request, f"Se crearon {creadas} oferta(s).")
            if duplicadas:
                messages.warning(request, f"{duplicadas} oferta(s) ya existían y se omitieron.")
            return redirect("academico:ofertas")
    else:
        form = OfertaBulkForm()

    return render(request, "academico/oferta_bulk_form.html", {"form": form, "nav_active": "academico"})

# ----------------- Periodos (gestión) -----------------

@requiere_gestion
def periodos_list(request):
    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio") or ""

    periodos = Periodo.objects.select_related("anio").all()
    if q:
        periodos = periodos.filter(Q(nombre__icontains=q) | Q(anio__nombre__icontains=q) | Q(numero__icontains=q))
    if anio_id:
        periodos = periodos.filter(anio_id=anio_id)

    periodos = periodos.order_by("-anio__activo", "-anio__nombre", "numero")

    paginator = Paginator(periodos, 12)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop("page", None)
    querystring = urlencode(params)

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "anio_selected": anio_id,
        "anios": AnioLectivo.objects.all().order_by("-activo", "-nombre"),
        "querystring": querystring,
        "nav_active": "academico",
    }
    return render(request, "academico/periodos.html", ctx)

@requiere_gestion
def periodo_create(request):
    if request.method == "POST":
        form = PeriodoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Periodo creado correctamente.")
            return redirect("academico:periodos")
    else:
        form = PeriodoForm()
    return render(request, "academico/periodo_form.html", {"form": form, "edit_mode": False, "nav_active": "academico"})

@requiere_gestion
def periodo_update(request, pk):
    obj = get_object_or_404(Periodo, pk=pk)
    if request.method == "POST":
        form = PeriodoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Periodo actualizado.")
            return redirect("academico:periodos")
    else:
        form = PeriodoForm(instance=obj)
    return render(request, "academico/periodo_form.html", {"form": form, "edit_mode": True, "obj": obj, "nav_active": "academico"})

@requiere_gestion
def periodo_delete(request, pk):
    obj = get_object_or_404(Periodo, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Periodo eliminado.")
        return redirect("academico:periodos")
    return render(request, "academico/periodo_confirm_delete.html", {"obj": obj, "nav_active": "academico"})

# ----------------- Logros (gestión) -----------------

@requiere_gestion
def logros_list(request):
    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio") or ""
    curso_id = request.GET.get("curso") or ""
    oferta_id = request.GET.get("oferta") or ""
    periodo_id = request.GET.get("periodo") or ""

    logros = Logro.objects.select_related("oferta", "oferta__anio", "oferta__curso", "oferta__asignatura", "periodo").all()

    if q:
        logros = logros.filter(
            Q(titulo__icontains=q) |
            Q(oferta__asignatura__nombre__icontains=q) |
            Q(oferta__curso__nombre__icontains=q) |
            Q(oferta__curso__grado__icontains=q) |
            Q(periodo__nombre__icontains=q) |
            Q(oferta__anio__nombre__icontains=q)
        )
    if anio_id:
        logros = logros.filter(oferta__anio_id=anio_id)
    if curso_id:
        logros = logros.filter(oferta__curso_id=curso_id)
    if oferta_id:
        logros = logros.filter(oferta_id=oferta_id)
    if periodo_id:
        logros = logros.filter(periodo_id=periodo_id)

    logros = logros.order_by("oferta__anio__nombre", "oferta__curso__grado", "oferta__asignatura__nombre", "periodo__numero", "titulo")

    paginator = Paginator(logros, 12)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    params = request.GET.copy()
    params.pop("page", None)
    querystring = urlencode(params)

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "anio_selected": anio_id,
        "curso_selected": curso_id,
        "oferta_selected": oferta_id,
        "periodo_selected": periodo_id,
        "anios": AnioLectivo.objects.all().order_by("-activo", "-nombre"),
        "cursos": Curso.objects.all().order_by("grado", "nombre"),
        "ofertas": AsignaturaOferta.objects.select_related("anio", "curso", "asignatura").all().order_by(
            "anio__nombre", "curso__grado", "curso__nombre", "asignatura__nombre"
        ),
        "periodos": Periodo.objects.select_related("anio").all().order_by("anio__nombre", "numero"),
        "querystring": querystring,
        "nav_active": "academico",
    }
    return render(request, "academico/logros.html", ctx)

@requiere_gestion
def logro_create(request):
    if request.method == "POST":
        form = LogroForm(request.POST)
        if form.is_valid():
            obj = form.save()
            total = Logro.objects.filter(oferta=obj.oferta, periodo=obj.periodo).aggregate(s=Sum("peso"))["s"] or Decimal("0")
            if total != Decimal("100"):
                messages.warning(request, f"Advertencia: la suma de pesos para esta oferta/periodo es {total}%, no 100%.")
            messages.success(request, "Logro creado correctamente.")
            return redirect("academico:logros")
    else:
        form = LogroForm()
    return render(request, "academico/logro_form.html", {"form": form, "edit_mode": False, "nav_active": "academico"})

@requiere_gestion
def logro_update(request, pk):
    obj = get_object_or_404(Logro, pk=pk)
    if request.method == "POST":
        form = LogroForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            total = Logro.objects.filter(oferta=obj.oferta, periodo=obj.periodo).aggregate(s=Sum("peso"))["s"] or Decimal("0")
            if total != Decimal("100"):
                messages.warning(request, f"Advertencia: la suma de pesos para esta oferta/periodo es {total}%, no 100%.")
            messages.success(request, "Logro actualizado.")
            return redirect("academico:logros")
    else:
        form = LogroForm(instance=obj)
    return render(request, "academico/logro_form.html", {"form": form, "edit_mode": True, "obj": obj, "nav_active": "academico"})

@requiere_gestion
def logro_delete(request, pk):
    obj = get_object_or_404(Logro, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Logro eliminado.")
        return redirect("academico:logros")
    return render(request, "academico/logro_confirm_delete.html", {"obj": obj, "nav_active": "academico"})

# ----------------- Asistencia (gestión) -----------------
@requiere_gestion
def asistencia_selector(request):
    """
    Selector de año / curso / periodo / fecha para ir a tomar asistencia.
    Docente de curso ve solo su curso_asignado; admin/rector ven todos.
    """
    docente = Docente.objects.filter(usuario=request.user).first()

    # Años lectivos
    anios = AnioLectivo.objects.all().order_by("-activo", "-nombre")

    # Cursos según rol
    if docente and not (request.user.is_staff or request.user.is_superuser):
        if docente.curso_asignado_id:
            cursos = Curso.objects.filter(pk=docente.curso_asignado_id)
        else:
            cursos = Curso.objects.none()
    else:
        cursos = Curso.objects.all().order_by("grado", "nombre")

    # Periodos (podríamos filtrar por año luego, pero de entrada todos)
    periodos = Periodo.objects.select_related("anio").all().order_by("anio__nombre", "numero")

    # Valores seleccionados (si viene algo por GET)
    anio_id = (request.GET.get("anio") or "").strip()
    curso_id = (request.GET.get("curso") or "").strip()
    periodo_id = (request.GET.get("periodo") or "").strip()
    fecha_str = (request.GET.get("fecha") or "").strip()

    if not fecha_str:
        fecha_str = date.today().isoformat()  # YYYY-MM-DD

    ctx = {
        "anios": anios,
        "cursos": cursos,
        "periodos": periodos,
        "anio_selected": anio_id,
        "curso_selected": curso_id,
        "periodo_selected": periodo_id,
        "fecha_selected": fecha_str,
        "nav_active": "academico",
    }
    return render(request, "academico/asistencia_selector.html", ctx)


@requiere_gestion
def asistencia_tomar(request):
    """
    Pantalla para pasar lista de un curso en una fecha.
    Crea (o reutiliza) un PaseLista y captura estados por estudiante.
    """
    from django.contrib import messages

    anio_id = request.GET.get("anio")
    curso_id = request.GET.get("curso")
    periodo_id = request.GET.get("periodo")
    fecha_str = request.GET.get("fecha")

    if not (anio_id and curso_id and periodo_id and fecha_str):
        messages.error(request, "Faltan parámetros. Selecciona año, curso, período y fecha.")
        return redirect("academico:asistencia_selector")

    try:
        fecha_val = date.fromisoformat(fecha_str)
    except ValueError:
        messages.error(request, "La fecha no es válida.")
        return redirect("academico:asistencia_selector")

    anio = get_object_or_404(AnioLectivo, pk=anio_id)
    curso = get_object_or_404(Curso, pk=curso_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id, anio=anio)

    docente = Docente.objects.filter(usuario=request.user).first()

    # Obtener o crear el pase de lista para ese curso/fecha/periodo/año
    pase, creado = PaseLista.objects.get_or_create(
        anio=anio,
        curso=curso,
        periodo=periodo,
        fecha=fecha_val,
        defaults={"docente": docente},
    )

    # Estudiantes del curso
    estudiantes = Estudiante.objects.filter(curso=curso).order_by("apellidos", "nombres")

    # Detalles existentes (si ya se pasó lista antes)
    existentes = {
        det.estudiante_id: det
        for det in AsistenciaDetalle.objects.filter(pase=pase).select_related("estudiante")
    }

    if request.method == "POST":
        guardados = 0
        for est in estudiantes:
            estado = request.POST.get(f"estado_{est.id}", "").strip()
            obs = (request.POST.get(f"obs_{est.id}") or "").strip()

            # Si no seleccionó nada, puedes ignorar o asumir "Presente"
            if not estado:
                # opcional: salta este estudiante
                continue

            AsistenciaDetalle.objects.update_or_create(
                pase=pase,
                estudiante=est,
                defaults={
                    "estado": estado,
                    "observacion": obs,
                },
            )
            guardados += 1

        messages.success(request, f"Asistencia guardada. Registros procesados: {guardados}.")
        # Recargar la misma página (GET) para ver lo guardado
        return redirect(
            f"{request.path}?anio={anio_id}&curso={curso_id}&periodo={periodo_id}&fecha={fecha_str}"
        )

    # Para el GET armamos filas con estado inicial
    filas = []
    for est in estudiantes:
        det = existentes.get(est.id)
        filas.append({
            "estudiante": est,
            "estado": det.estado if det else AsistenciaDetalle.PRESENTE,
            "observacion": det.observacion if det else "",
        })

    ctx = {
        "anio": anio,
        "curso": curso,
        "periodo": periodo,
        "fecha": fecha_val,
        "pase": pase,
        "filas": filas,
        "nav_active": "academico",
    }
    return render(request, "academico/asistencia_tomar.html", ctx)
# ----------------- Notas (gestión) -----------------

@requiere_gestion
def notas_selector(request):
    # 1. Detectar si el usuario es docente
    docente = Docente.objects.filter(usuario=request.user).first()

    # 2. Ofertas base según el rol
    base_ofertas = AsignaturaOferta.objects.select_related("anio", "curso", "asignatura")

    if docente and not (request.user.is_staff or request.user.is_superuser):
        # Docente solo ve sus ofertas
        base_ofertas = base_ofertas.filter(docente=docente)

    # 3. Años / cursos base según el rol
    if docente and not request.user.is_staff and not request.user.is_superuser:
        # Solo años con ofertas del docente
        anios = (
            AnioLectivo.objects
            .filter(ofertas__in=base_ofertas)
            .distinct()
            .order_by("-activo", "-nombre")
        )

        # Cursos que el docente atiende (sin filtrar aún por año)
        cursos = (
            Curso.objects
            .filter(ofertas__in=base_ofertas)
            .distinct()
            .order_by("grado", "nombre")
        )
    else:
        # Admin/directivo ve todo
        anios = AnioLectivo.objects.all().order_by("-activo", "-nombre")
        cursos = Curso.objects.all().order_by("grado", "nombre")

    # 4. Parámetros GET
    anio_id = (request.GET.get("anio") or "").strip()
    curso_id = (request.GET.get("curso") or "").strip()
    oferta_id = (request.GET.get("oferta") or "").strip()
    periodo_id = (request.GET.get("periodo") or "").strip()

    ofertas = base_ofertas
    periodos = Periodo.objects.select_related("anio")

    # 5. Filtros según lo escogido

    # Si hay año → filtrar ofertas, periodos y cursos por ese año
    if anio_id:
        ofertas = ofertas.filter(anio_id=anio_id)
        periodos = periodos.filter(anio_id=anio_id)

        # Cursos que tienen ofertas en ese año (según el rol)
        cursos = (
            Curso.objects
            .filter(ofertas__in=ofertas)
            .distinct()
            .order_by("grado", "nombre")
        )

    # Si hay curso → filtrar ofertas por curso
    if curso_id:
        ofertas = ofertas.filter(curso_id=curso_id)

    ofertas = ofertas.order_by(
        "anio__nombre",
        "curso__grado",
        "curso__nombre",
        "asignatura__nombre",
    )

    periodos = periodos.order_by("numero")

    ctx = {
        "anios": anios,
        "cursos": cursos,
        "ofertas": ofertas,
        "periodos": periodos,
        "anio_selected": anio_id,
        "curso_selected": curso_id,
        "oferta_selected": oferta_id,
        "periodo_selected": periodo_id,
        "nav_active": "academico",
        "docente": docente,
    }
    return render(request, "academico/notas_selector.html", ctx)

@requiere_gestion
def notas_capturar(request):
    anio_id = request.GET.get("anio")
    curso_id = request.GET.get("curso")
    oferta_id = request.GET.get("oferta")
    periodo_id = request.GET.get("periodo")

    if not (anio_id and curso_id and oferta_id and periodo_id):
        messages.error(request, "Faltan parámetros. Selecciona año, curso, oferta y periodo.")
        return redirect("academico:notas_selector")

    oferta = get_object_or_404(
        AsignaturaOferta.objects.select_related("anio", "curso", "asignatura"),
        pk=oferta_id, anio_id=anio_id, curso_id=curso_id
    )
    periodo = get_object_or_404(
        Periodo.objects.select_related("anio"),
        pk=periodo_id,
        anio_id=anio_id
    )

    if oferta.anio_id != periodo.anio_id:
        messages.error(request, "La oferta y el periodo pertenecen a años diferentes.")
        return redirect("academico:notas_selector")

    estudiantes = Estudiante.objects.filter(
        curso_id=curso_id
    ).order_by("apellidos", "nombres")

    logros = Logro.objects.filter(
        oferta_id=oferta.id,
        periodo_id=periodo.id
    ).order_by("titulo")

    if not estudiantes.exists():
        messages.warning(request, "Este curso no tiene estudiantes. Primero registra estudiantes.")
        return redirect("academico:notas_selector")

    # ───────────── actividades por logro ─────────────
    actividades_por_logro = {
        lg.id: list(Actividad.objects.filter(logro=lg).order_by("id"))
        for lg in logros
    }

    # ───────────── notas finales de logro (tabla CalificacionLogro) ─────────────
    existentes = {
        (c.estudiante_id, c.logro_id): c.nota
        for c in CalificacionLogro.objects.filter(
            logro__in=logros,
            estudiante__in=estudiantes
        )
    }

    # 🔹 Reorganizamos a diccionario anidado: notas[est_id][logro_id] = nota
    notas_por_estudiante_logro = {}
    for (est_id, logro_id), nota in existentes.items():
        notas_por_estudiante_logro.setdefault(est_id, {})[logro_id] = nota

    # (puedes dejar o quitar estos prints si quieres)
    print("\n======= DEBUG NOTAS CAPTURAR =======")
    print("Logros cargados (IDs):", [lg.id for lg in logros])
    print("Estudiantes cargados (IDs):", [e.id for e in estudiantes])
    print("\nActividades por logro:")
    for lg_id, acts in actividades_por_logro.items():
        print(f"  Logro {lg_id}: {len(acts)} actividades")
    print("\nNotas por estudiante/logro:")
    print(notas_por_estudiante_logro)
    print("======= FIN DEBUG =======\n")

    ctx = {
        "oferta": oferta,
        "periodo": periodo,
        "estudiantes": estudiantes,
        "logros": logros,
        "actividades_por_logro": actividades_por_logro,
        "notas_por_estudiante_logro": notas_por_estudiante_logro,
        "ya_hay_notas": bool(existentes),
        "nav_active": "academico",
    }
    return render(request, "academico/notas_capturar.html", ctx)



@requiere_gestion
def actividad_create(request, logro_id):
    logro = get_object_or_404(Logro, pk=logro_id)

    if request.method == "POST":
        titulo = request.POST.get("titulo")
        peso = request.POST.get("peso") or "0"
        Actividad.objects.create(
            logro=logro,
            titulo=titulo,
            peso=Decimal(peso)
        )
        messages.success(request, "Actividad creada.")
        return redirect("academico:actividades", logro_id=logro.id)

    return render(request, "academico/actividad_form.html", {"logro": logro})

@requiere_gestion
def notas_actividades_capturar(request, actividad_id):
    actividad = get_object_or_404(Actividad, pk=actividad_id)
    logro = actividad.logro
    estudiantes = list(
        Estudiante.objects
        .filter(curso=logro.oferta.curso)
        .order_by("apellidos", "nombres")
    )

    existentes = {
        c.estudiante_id: c.nota
        for c in CalificacionActividad.objects.filter(actividad=actividad)
    }

    if request.method == "POST":
        guardados = 0
        for est in estudiantes:
            raw = (request.POST.get(f"nota_{est.id}", "")).strip()
            if raw == "":
                CalificacionActividad.objects.filter(
                    actividad=actividad,
                    estudiante=est
                ).delete()
                continue

            try:
                val = Decimal(raw.replace(",", "."))
            except:
                continue

            CalificacionActividad.objects.update_or_create(
                actividad=actividad,
                estudiante=est,
                defaults={"nota": val}
            )
            guardados += 1
            recalcular_nota_logro_desde_actividades(est, logro)

        messages.success(request, "Notas de actividades guardadas.")
        return redirect("academico:actividades", logro_id=logro.id)

    # 👉 aquí “inyectamos” la nota existente en cada estudiante
    for est in estudiantes:
        est.nota_actividad = existentes.get(est.id)

    return render(request, "academico/notas_actividades_capturar.html", {
        "actividad": actividad,
        "logro": logro,
        "estudiantes": estudiantes,
        "nav_active": "academico",
    })

@requiere_gestion
def saber_ser_capturar(request, oferta_id, periodo_id):
    oferta = get_object_or_404(AsignaturaOferta, pk=oferta_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id)

    estudiantes = list(
        Estudiante.objects
        .filter(curso=oferta.curso)
        .order_by("apellidos", "nombres")
    )

    # Traemos TODOS los registros existentes
    existentes = {
        ss.estudiante_id: ss
        for ss in SaberSer.objects.filter(
            asignatura_oferta=oferta,
            periodo=periodo
        )
    }

    def _parse_decimal(raw):
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            return Decimal(raw.replace(",", "."))
        except:
            return None

    if request.method == "POST":
        guardados = 0

        for est in estudiantes:
            raw_comp = request.POST.get(f"comp_{est.id}", "")
            raw_resp = request.POST.get(f"resp_{est.id}", "")
            raw_auto = request.POST.get(f"auto_{est.id}", "")

            val_comp = _parse_decimal(raw_comp)
            val_resp = _parse_decimal(raw_resp)
            val_auto = _parse_decimal(raw_auto)

            # Si las tres vienen vacías → borramos registro (si existe) y pasamos al siguiente
            if val_comp is None and val_resp is None and val_auto is None:
                SaberSer.objects.filter(
                    estudiante=est,
                    asignatura_oferta=oferta,
                    periodo=periodo,
                ).delete()
                continue

            SaberSer.objects.update_or_create(
                estudiante=est,
                asignatura_oferta=oferta,
                periodo=periodo,
                defaults={
                    "anio": oferta.anio,
                    "nota_comportamiento": val_comp,
                    "nota_responsabilidad": val_resp,
                    "nota_autoevaluacion": val_auto,
                }
            )
            guardados += 1

        messages.success(request, f"Notas de Saber Ser guardadas ({guardados} registros).")
        return redirect("academico:notas_selector")

    # GET: inyectamos las 3 notas existentes a cada estudiante
    for est in estudiantes:
        ss = existentes.get(est.id)
        if ss:
            est.nota_saber_ser_comp = ss.nota_comportamiento
            est.nota_saber_ser_resp = ss.nota_responsabilidad
            est.nota_saber_ser_auto = ss.nota_autoevaluacion
        else:
            est.nota_saber_ser_comp = None
            est.nota_saber_ser_resp = None
            est.nota_saber_ser_auto = None

    return render(request, "academico/saber_ser_capturar.html", {
        "oferta": oferta,
        "periodo": periodo,
        "estudiantes": estudiantes,
        "nav_active": "academico",
    })

# ----------------- Boletines -----------------

def _concepto_letra(n):
    if n is None:
        return "N.A."
    n = Decimal(n)
    if n >= Decimal("4.60"): return "S"
    if n >= Decimal("4.00"): return "A"
    if n >= Decimal("3.00"): return "B"
    return "D"

def _contexto_boletin(anio, curso, periodo, est):
    """
    Copia aquí la parte de tu vista 'boletin_estudiante_pdf' que arma el ctx:
    areas, promedios, obs_general, etc.
    """
    # TODO: este es solo un esquema; tú llenas el contexto real
    # return ctx
    ...

def _boletin_pdf_bytes(request, anio, curso, periodo, est):
    ctx = _contexto_boletin(anio, curso, periodo, est)
    html = render_to_string("academico/boletin_estudiante_pdf.html", ctx)
    pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    return pdf_bytes


@requiere_gestion
def boletines_masivos(request):
    # protección básica
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "No tiene permisos para descargar boletines masivos.")
        return redirect("academico:boletin_selector")

    if request.method != "POST":
        return redirect("academico:boletin_selector")

    anio_id    = request.POST.get("anio")
    curso_id   = request.POST.get("curso")
    periodo_id = request.POST.get("periodo")
    est_ids    = request.POST.getlist("estudiantes")

    if not (anio_id and curso_id and periodo_id):
        messages.error(request, "Faltan parámetros (año, curso, periodo).")
        return redirect("academico:boletin_selector")

    if not est_ids:
        messages.warning(request, "No seleccionó ningún estudiante.")
        url = f"{reverse('academico:boletin_selector')}?anio={anio_id}&curso={curso_id}&periodo={periodo_id}"
        return redirect(url)

    anio    = get_object_or_404(AnioLectivo, pk=anio_id)
    curso   = get_object_or_404(Curso, pk=curso_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id, anio=anio)

    estudiantes = (
        Estudiante.objects
        .filter(id__in=est_ids, curso=curso)
        .order_by("apellidos", "nombres")
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for est in estudiantes:
            pdf_bytes = _boletin_pdf_bytes(request, anio, curso, periodo, est)
            filename = f"Boletin_{est.apellidos}_{est.nombres}_{periodo.nombre}.pdf"
            zip_file.writestr(filename, pdf_bytes)

    buffer.seek(0)
    filename_zip = f"Boletines_{curso.grado}_{curso.nombre}_{periodo.nombre}.zip"
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename=\"{filename_zip}\"'
    return response

def boletin_trimestral(request, estudiante_id, anio_id, trimestre):
    estudiante = get_object_or_404(Estudiante, pk=estudiante_id)
    anio = get_object_or_404(AnioEconomico, pk=anio_id)

    resumen = resumen_cartera_para_boletin(estudiante, anio, int(trimestre))

    if not resumen["puede_ver"]:
        # Vista bloqueada
        return render(
            request,
            "academico/boletin_bloqueado_cartera.html",
            {
                "estudiante": estudiante,
                "trimestre": trimestre,
                **resumen,
            },
        )
    return render(
        request,
        "academico/boletin_trimestral.html",
        {
            "estudiante": estudiante,
            "trimestre": trimestre,
            "anio": anio,

        },
    )

@requiere_gestion
def boletin_selector(request):
    anio_id = (request.GET.get("anio") or "").strip()
    curso_id = (request.GET.get("curso") or "").strip()
    periodo_id = (request.GET.get("periodo") or "").strip()

    anios = AnioLectivo.objects.all().order_by("-activo", "-nombre")

    if anio_id:
        cursos = (
            Curso.objects
            .filter(ofertas__anio_id=anio_id)
            .distinct()
            .order_by("grado", "nombre")
        )
        periodos = (
            Periodo.objects
            .filter(anio_id=anio_id)
            .order_by("numero")
        )
    else:
        cursos = Curso.objects.all().order_by("grado", "nombre")
        periodos = Periodo.objects.select_related("anio").all().order_by("anio__nombre", "numero")

    estudiantes = []
    if curso_id:
        estudiantes = Estudiante.objects.filter(curso_id=curso_id).order_by("apellidos", "nombres")

    # 👉 aquí defines quién puede descargar masivo
    tiene_permiso_masivo = (
        request.user.is_superuser
        or request.user.is_staff   # o cambia por tu lógica de rector / coordinador
        # or getattr(request.user, "es_rector", False)
        # or getattr(request.user, "es_coordinador", False)
    )

    ctx = {
        "anios": anios,
        "cursos": cursos,
        "periodos": periodos,
        "anio_selected": anio_id,
        "curso_selected": curso_id,
        "periodo_selected": periodo_id,
        "estudiantes": estudiantes,
        "tiene_permiso_masivo": tiene_permiso_masivo,
        "nav_active": "academico",
    }
    return render(request, "academico/boletin_selector.html", ctx)

@requiere_gestion
def boletin_generar(request):
    anio_id = request.GET.get("anio")
    curso_id = request.GET.get("curso")
    periodo_id = request.GET.get("periodo")

    if not (anio_id and curso_id and periodo_id):
        messages.error(request, "Debes seleccionar año, curso y periodo.")
        return redirect("academico:boletin_selector")

    periodo = get_object_or_404(Periodo, pk=periodo_id)
    curso = get_object_or_404(Curso, pk=curso_id)
    estudiantes = Estudiante.objects.filter(curso=curso).order_by("apellidos", "nombres")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="boletines_{curso}_{periodo}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    for est in estudiantes:
        story.append(Paragraph(f"<b>Estudiante:</b> {est.nombres} {est.apellidos}", styles["Normal"]))
        story.append(Paragraph(f"<b>Curso:</b> {curso}", styles["Normal"]))
        story.append(Paragraph(f"<b>Periodo:</b> {periodo.nombre}", styles["Normal"]))
        story.append(Spacer(1, 10))

        data = [["Asignatura", "Logro", "Nota", "Peso %"]]
        calificaciones = (
            CalificacionLogro.objects
            .filter(estudiante=est, logro__periodo=periodo)
            .select_related("logro__oferta__asignatura")
        )
        for c in calificaciones:
            data.append([
                c.logro.oferta.asignatura.nombre,
                c.logro.titulo,
                f"{c.nota:.2f}",
                f"{c.logro.peso}%",
            ])
        if len(data) == 1:
            data.append(["Sin calificaciones registradas", "", "", ""])

        table = Table(data, colWidths=[130, 250, 60, 60])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("ALIGN", (2, 1), (3, -1), "CENTER"),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))

    doc.build(story)
    return response

from .models import (
    AnioLectivo, Curso, Periodo, Estudiante,
    AsignaturaOferta, Logro, CalificacionLogro,
    AsistenciaDetalle, Observador,
    ObservacionBoletin,   # Asegúrate de tener este modelo
)

# y helpers que ya usas en otros lados (PDF):
# _promedio_asignatura_periodo, _concepto_letra,
# ranking_curso_periodo, ranking_curso_anual, _puede_gestionar


@requiere_gestion
def boletin_estudiante(request):
    anio_id    = request.GET.get("anio")
    curso_id   = request.GET.get("curso")
    periodo_id = request.GET.get("periodo")
    est_id     = request.GET.get("estudiante")

    if not (anio_id and curso_id and periodo_id and est_id):
        messages.error(request, "Faltan parámetros (año, curso, periodo, estudiante).")
        return redirect("academico:boletin_selector")

    anio    = get_object_or_404(AnioLectivo, pk=anio_id)
    curso   = get_object_or_404(Curso, pk=curso_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id, anio=anio)
    est     = get_object_or_404(Estudiante, pk=est_id, curso=curso)

    # ====== OFERTAS (asignaturas del curso en ese año) ======
    ofertas = (
        AsignaturaOferta.objects
        .select_related("asignatura", "docente")
        .filter(anio=anio, curso=curso)
        .order_by("asignatura__area", "asignatura__nombre")
    )

    # ====== RESUMEN DE TRES TRIMESTRES (igual que ya tenías) ======
    periodos_anio = list(
        Periodo.objects.filter(anio=anio).order_by("numero")[:3]
    )

    resumen_asignaturas = []

    for of in ofertas:
        fila_resumen = {
            "asignatura": of.asignatura.nombre,
        }
        proms_validos = []

        for idx, per in enumerate(periodos_anio, start=1):
            prom_p = _promedio_asignatura_periodo(est, of, per)
            clave = f"p{idx}"  # p1, p2, p3
            fila_resumen[clave] = prom_p
            if prom_p is not None:
                proms_validos.append(prom_p)

        prom_final = None
        if proms_validos:
            prom_final = (sum(proms_validos) / len(proms_validos)).quantize(Decimal("0.01"))

        fila_resumen["prom_final"]  = prom_final
        fila_resumen["letra_final"] = _concepto_letra(prom_final)

        resumen_asignaturas.append(fila_resumen)

    # Promedios globales por trimestre
    promedios_trimestre = []
    for per in periodos_anio:
        notas = []
        for of in ofertas:
            p = _promedio_asignatura_periodo(est, of, per)
            if p is not None:
                notas.append(p)
        prom = None
        if notas:
            prom = (sum(notas) / len(notas)).quantize(Decimal("0.01"))
        promedios_trimestre.append(prom)

    # Promedio anual
    notas_validas  = [p for p in promedios_trimestre if p is not None]
    promedio_anual = None
    if notas_validas:
        promedio_anual = (sum(notas_validas) / len(notas_validas)).quantize(Decimal("0.01"))

    # === NUEVO: mapa asignatura -> resumen (para la tabla tipo PDF) ===
    resumen_por_asig = {r["asignatura"]: r for r in resumen_asignaturas}

    # ====== AGRUPAR POR ÁREA (logros + notas del periodo actual) ======
    areas_dict = defaultdict(list)

    for of in ofertas:
        area_nombre = of.asignatura.area or "Otras áreas"

        logros = Logro.objects.filter(oferta=of, periodo=periodo).order_by("titulo")
        cals = (
            CalificacionLogro.objects
            .filter(estudiante=est, logro__in=logros)
            .select_related("logro")
        )

        detalle = []
        suma_pesada = Decimal("0")
        suma_pesos  = Decimal("0")
        notas_por_logro = {c.logro_id: c.nota for c in cals}

        for lg in logros:
            nota = notas_por_logro.get(lg.id)
            detalle.append({"titulo": lg.titulo, "peso": lg.peso, "nota": nota})
            if nota is not None:
                suma_pesada += Decimal(nota) * (lg.peso / Decimal("100"))
                suma_pesos  += (lg.peso / Decimal("100"))

        promedio = None
        if suma_pesos > 0:
            promedio = (suma_pesada / suma_pesos).quantize(Decimal("0.01"))

        fila = {
            "asignatura": of.asignatura.nombre,
            "docente": f"{of.docente.apellidos} {of.docente.nombres}" if of.docente else "—",
            "promedio": promedio,
            "letra": _concepto_letra(promedio),
            "detalle": detalle,
        }

        areas_dict[area_nombre].append(fila)

    areas = [
        {"nombre": nombre, "filas": filas}
        for nombre, filas in areas_dict.items()
    ]
    areas.sort(key=lambda a: a["nombre"])

    # ====== OBSERVADOR (si lo quieres seguir mostrando en otro lado) ======
    observaciones = (
        Observador.objects
        .filter(
            estudiante=est,
            fecha__gte=periodo.anio.fecha_inicio,
            fecha__lte=periodo.anio.fecha_fin
        )
        .order_by("fecha")
    )

    # ====== ASISTENCIA: fallas y tardanzas del período ======
    total_fallas_periodo = AsistenciaDetalle.objects.filter(
        estudiante=est,
        estado=AsistenciaDetalle.AUSENTE,
        pase__anio=anio,
        pase__curso=curso,
        pase__periodo=periodo,
    ).count()

    total_tardanzas_periodo = AsistenciaDetalle.objects.filter(
        estudiante=est,
        estado=AsistenciaDetalle.TARDANZA,
        pase__anio=anio,
        pase__curso=curso,
        pase__periodo=periodo,
    ).count()

    # ====== OBSERVACIÓN GENERAL DEL BOLETÍN (como en el PDF) ======
    obs_general = ObservacionBoletin.objects.filter(
        estudiante=est,
        periodo=periodo
    ).first()

    # ====== PUESTOS POR TRIMESTRE Y ANUAL (si tienes estas funciones) ======
    puestos_trimestres = []
    for per in periodos_anio:
        mapa_puestos = ranking_curso_periodo(anio, curso, per)  # {est_id: puesto}
        puestos_trimestres.append(mapa_puestos)

    puesto_p1 = puestos_trimestres[0].get(est.id) if len(puestos_trimestres) > 0 else None
    puesto_p2 = puestos_trimestres[1].get(est.id) if len(puestos_trimestres) > 1 else None
    puesto_p3 = puestos_trimestres[2].get(est.id) if len(puestos_trimestres) > 2 else None

    puestos_anual = ranking_curso_anual(anio, curso)  # {est_id: puesto}
    puesto_final  = puestos_anual.get(est.id)

    ctx = {
        "anio": anio,
        "curso": curso,
        "periodo": periodo,
        "estudiante": est,
        "areas": areas,
        "observaciones": observaciones,
        "es_docente": _puede_gestionar(request.user),

        "total_fallas_periodo": total_fallas_periodo,
        "total_tardanzas_periodo": total_tardanzas_periodo,

        "resumen_asignaturas": resumen_asignaturas,
        "resumen_por_asig": resumen_por_asig,
        "promedios_trimestre": promedios_trimestre,
        "promedio_anual": promedio_anual,

        "obs_general": obs_general,
        "puesto_p1": puesto_p1,
        "puesto_p2": puesto_p2,
        "puesto_p3": puesto_p3,
        "puesto_final": puesto_final,
    }
    return render(request, "academico/boletin_estudiante.html", ctx)


def boletin_estudiante_pdf(request):
    anio_id     = request.GET.get("anio")
    curso_id    = request.GET.get("curso")
    periodo_id  = request.GET.get("periodo")
    est_id      = request.GET.get("estudiante")

    # Validación de parámetros
    if not (anio_id and curso_id and periodo_id and est_id):
        messages.error(request, "Faltan parámetros para generar el boletín en PDF.")
        return redirect("academico:boletin_selector")

    # Obtener objetos base
    anio    = get_object_or_404(AnioLectivo, pk=anio_id)
    curso   = get_object_or_404(Curso, pk=curso_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id, anio=anio)
    est     = get_object_or_404(Estudiante, pk=est_id, curso=curso)

    # Ofertas (asignaturas) del curso en ese año
    ofertas = (
        AsignaturaOferta.objects
        .select_related("asignatura", "docente")
        .filter(anio=anio, curso=curso)
        .order_by("asignatura__area", "asignatura__nombre")
    )

    # ========================================
    #   RESUMEN DE TRES TRIMESTRES
    # ========================================
    periodos_anio = list(
        Periodo.objects.filter(anio=anio).order_by("numero")[:3]
    )

    resumen_asignaturas = []

    for of in ofertas:
        fila_res = {
            "asignatura": of.asignatura.nombre,
            "p1": None,
            "p2": None,
            "p3": None,
        }

        proms_validos = []

        for idx, per in enumerate(periodos_anio, start=1):
            prom_p = _promedio_asignatura_periodo(est, of, per)
            clave = f"p{idx}"
            fila_res[clave] = prom_p
            if prom_p is not None:
                proms_validos.append(prom_p)

        prom_final = None
        if proms_validos:
            prom_final = (sum(proms_validos) / len(proms_validos)).quantize(Decimal("0.01"))

        fila_res["prom_final"]  = prom_final
        fila_res["letra_final"] = _concepto_letra(prom_final)

        resumen_asignaturas.append(fila_res)

    # Promedios globales por trimestre
    promedios_trimestre = []
    for per in periodos_anio:
        notas = []
        for of in ofertas:
            p = _promedio_asignatura_periodo(est, of, per)
            if p is not None:
                notas.append(p)
        prom = None
        if notas:
            prom = (sum(notas) / len(notas)).quantize(Decimal("0.01"))
        promedios_trimestre.append(prom)

    # Promedio anual
    notas_validas  = [p for p in promedios_trimestre if p is not None]
    promedio_anual = None
    if notas_validas:
        promedio_anual = (sum(notas_validas) / len(notas_validas)).quantize(Decimal("0.01"))

    puestos_trimestres = []
    for per in periodos_anio:
        mapa_puestos = ranking_curso_periodo(anio, curso, per)
        puestos_trimestres.append(mapa_puestos)

    # Extraemos el puesto de ESTE estudiante en cada trimestre
    puesto_p1 = puestos_trimestres[0].get(est.id) if len(puestos_trimestres) > 0 else None
    puesto_p2 = puestos_trimestres[1].get(est.id) if len(puestos_trimestres) > 1 else None
    puesto_p3 = puestos_trimestres[2].get(est.id) if len(puestos_trimestres) > 2 else None

    # Puesto final (anual)
    puestos_anual = ranking_curso_anual(anio, curso)
    puesto_final = puestos_anual.get(est.id)
    # ========================================
    #   ÁREAS / ASIGNATURAS (detalle por logros)
    # ========================================
    areas_dict = defaultdict(list)

    for of in ofertas:
        area_nombre = of.asignatura.area or "Otras áreas"

        logros = Logro.objects.filter(oferta=of, periodo=periodo).order_by("titulo")
        cals = (
            CalificacionLogro.objects
            .filter(estudiante=est, logro__in=logros)
            .select_related("logro")
        )

        detalle = []
        suma_pesada = Decimal("0")
        suma_pesos  = Decimal("0")
        notas_por_logro = {c.logro_id: c.nota for c in cals}

        for lg in logros:
            nota = notas_por_logro.get(lg.id)
            detalle.append({
                "titulo": lg.titulo,
                "peso": lg.peso,
                "nota": nota,
            })
            if nota is not None:
                suma_pesada += Decimal(nota) * (lg.peso / Decimal("100"))
                suma_pesos  += (lg.peso / Decimal("100"))

        promedio = None
        if suma_pesos > 0:
            promedio = (suma_pesada / suma_pesos).quantize(Decimal("0.01"))

        fila = {
            "asignatura": of.asignatura.nombre,
            "docente": f"{of.docente.apellidos} {of.docente.nombres}" if of.docente else "—",
            "promedio": promedio,
            "letra": _concepto_letra(promedio),
            "detalle": detalle,
        }
        areas_dict[area_nombre].append(fila)

    areas = [
        {"nombre": nombre, "filas": filas}
        for nombre, filas in areas_dict.items()
    ]
    areas.sort(key=lambda a: a["nombre"])

    # Observación general (si existe)
    obs_general = ObservacionBoletin.objects.filter(
        estudiante=est,
        periodo=periodo
    ).first()

    # ========= RESUMEN DE FALLAS DEL PERÍODO =========
    total_fallas_periodo = AsistenciaDetalle.objects.filter(
        estudiante=est,
        estado=AsistenciaDetalle.AUSENTE,  # solo ausencias
        pase__anio=anio,
        pase__curso=curso,
        pase__periodo=periodo,
    ).count()
    total_tardanzas_periodo = AsistenciaDetalle.objects.filter(
        estudiante=est,
        estado=AsistenciaDetalle.TARDANZA,  # 👈 tardanzas
        pase__anio=anio,
        pase__curso=curso,
        pase__periodo=periodo,
    ).count()

    # ========= NOMBRES DOCENTE CURSO Y RECTOR ACTIVO =========
    # Docente encargado del curso (Curso asignado)
    docente_curso = Docente.objects.filter(curso_asignado=curso).first()
    if docente_curso:
        docente_nombre = f"{docente_curso.nombres} {docente_curso.apellidos}".upper()
    else:
        docente_nombre = "DOCENTE"

    # Rector activo (primer usuario activo del grupo "Rector")
    rector_user = (
        User.objects
        .filter(is_active=True, groups__name="Rector")
        .select_related("docente")
        .first()
    )
    if rector_user:
        if hasattr(rector_user, "docente"):
            rector_nombre = f"{rector_user.docente.nombres} {rector_user.docente.apellidos}".upper()
        else:
            rector_nombre = (rector_user.get_full_name() or rector_user.username).upper()
    else:
        rector_nombre = "RECTOR(A)"

    # ========= MAPA asignatura -> resumen (para el template) =========
    resumen_por_asig = {r["asignatura"]: r for r in resumen_asignaturas}

    # ========= Contexto para el template HTML =========
    logo_url = request.build_absolute_uri(static("img/logo.png"))
    sello_url = request.build_absolute_uri(static("img/sello.png"))

    ctx = {
        "anio": anio,
        "curso": curso,
        "periodo": periodo,
        "estudiante": est,
        "areas": areas,
        "obs_general": obs_general,
        "total_fallas_periodo": total_fallas_periodo,
        "total_tardanzas_periodo": total_tardanzas_periodo,
        "resumen_asignaturas": resumen_asignaturas,
        "resumen_por_asig": resumen_por_asig,
        "promedios_trimestre": promedios_trimestre,
        "promedio_anual": promedio_anual,
        "docente_nombre": docente_nombre,
        "rector_nombre": rector_nombre,
        "logo_url": logo_url,
        "sello_url": sello_url,
        "puesto_p1": puesto_p1,
        "puesto_p2": puesto_p2,
        "puesto_p3": puesto_p3,
        "puesto_final": puesto_final,
    }

    # =============== GENERAR PDF CON WEASYPRINT ===============
    html_string = render_to_string("academico/boletin_estudiante_pdf.html", ctx)

    response = HttpResponse(content_type="application/pdf")
    filename = f"boletin_{est.apellidos}_{est.nombres}_{periodo.nombre}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(response)
    return response

@requiere_gestion
def observacion_nueva(request):
    est_id = request.GET.get("estudiante")
    periodo_id = request.GET.get("periodo")

    if not (est_id and periodo_id):
        messages.error(request, "Faltan parámetros (estudiante y periodo).")
        return redirect("academico:boletin_selector")

    estudiante = get_object_or_404(Estudiante, pk=est_id)
    periodo = get_object_or_404(Periodo, pk=periodo_id)

    # Intentamos obtener el docente logueado (si existe vinculación)
    docente = Docente.objects.filter(usuario=request.user).first()

    if request.method == "POST":
        texto = (request.POST.get("detalle") or "").strip()

        if not texto:
            messages.error(request, "Escribe alguna observación antes de guardar.")
        else:
            # 🔹 Se guarda SIEMPRE en ObservacionBoletin
            obj, created = ObservacionBoletin.objects.update_or_create(
                estudiante=estudiante,
                periodo=periodo,
                defaults={
                    "docente": docente,
                    "texto": texto,
                },
            )
            messages.success(
                request,
                "Observación guardada correctamente." if created else "Observación actualizada correctamente."
            )

            # Redirigimos de vuelta al boletín de ese estudiante
            url = (
                f"{reverse('academico:boletin_estudiante')}"
                f"?anio={periodo.anio_id}"
                f"&curso={estudiante.curso_id}"
                f"&periodo={periodo.id}"
                f"&estudiante={estudiante.id}"
            )
            return redirect(url)

    ctx = {
        "estudiante": estudiante,
        "periodo": periodo,
        "nav_active": "academico",
    }
    return render(request, "academico/observacion_form.html", ctx)

def _promedio_asignatura_periodo(estudiante, oferta, periodo):
    """
    Calcula el promedio (0–5) de una asignatura para un estudiante
    en un periodo, usando:
      - Logros (90%)
      - Saber Ser (10%) si existe
    """
    # 1) Nota por logros (como antes)
    logros = Logro.objects.filter(oferta=oferta, periodo=periodo).order_by("titulo")
    cals = (
        CalificacionLogro.objects
        .filter(estudiante=estudiante, logro__in=logros)
        .select_related("logro")
    )

    notas_por_logro = {c.logro_id: c.nota for c in cals}

    suma_pesada = Decimal("0")
    suma_pesos = Decimal("0")

    for lg in logros:
        nota = notas_por_logro.get(lg.id)
        if nota is not None:
            peso_rel = lg.peso / Decimal("100")
            suma_pesada += Decimal(nota) * peso_rel
            suma_pesos += peso_rel

    nota_logros = None
    if suma_pesos > 0:
        nota_logros = (suma_pesada / suma_pesos).quantize(Decimal("0.01"))

    # si no hay logros con nota, no hay promedio
    if nota_logros is None:
        return None

    # 2) Buscar Saber Ser (opcional)
    ss = SaberSer.objects.filter(
        estudiante=estudiante,
        asignatura_oferta=oferta,
        periodo=periodo,
        anio=oferta.anio,
    ).first()

    if ss and ss.nota is not None:
        final = (nota_logros * LOGROS_PESO) + (Decimal(ss.nota) * SABER_SER_PESO)
        return final.quantize(Decimal("0.01"))

    # Si no hay Saber Ser, devolvemos sólo logros
    return nota_logros

def es_directivo(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Si usas grupos "Rector" y "Coordinador"
    return user.groups.filter(name__in=["Rector", "Coordinador"]).exists()


@login_required
@user_passes_test(es_directivo)
def anios_lectivos_list(request):
    """
    Listado de años lectivos + botón para crear uno nuevo.
    """
    anios = AnioLectivo.objects.all().order_by("-nombre")
    context = {
        "anios": anios,
        "nav_active": "academico",
    }
    return render(request, "academico/anios_lectivos_list.html", context)


@login_required
@user_passes_test(es_directivo)
def anio_lectivo_create(request):
    """
    Crear un nuevo año lectivo.
    """
    if request.method == "POST":
        form = AnioLectivoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Año lectivo creado correctamente.")
            return redirect("academico:anios_lectivos")
    else:
        form = AnioLectivoForm()

    context = {
        "form": form,
        "edit_mode": False,
        "nav_active": "academico",
    }
    return render(request, "academico/anio_lectivo_form.html", context)


@login_required
@user_passes_test(es_directivo)
def anio_lectivo_update(request, pk):
    """
    Editar un año lectivo existente.
    """
    anio = get_object_or_404(AnioLectivo, pk=pk)

    if request.method == "POST":
        form = AnioLectivoForm(request.POST, instance=anio)
        if form.is_valid():
            form.save()
            messages.success(request, "Año lectivo actualizado correctamente.")
            return redirect("academico:anios_lectivos")
    else:
        form = AnioLectivoForm(instance=anio)

    context = {
        "form": form,
        "edit_mode": True,
        "obj": anio,
        "nav_active": "academico",
    }
    return render(request, "academico/anio_lectivo_form.html", context)


@login_required
@user_passes_test(es_directivo)
def anio_lectivo_delete(request, pk):
    """
    Eliminar un año lectivo (si se requiere).
    """
    anio = get_object_or_404(AnioLectivo, pk=pk)

    if request.method == "POST":
        anio.delete()
        messages.success(request, "Año lectivo eliminado correctamente.")
        return redirect("academico:anios_lectivos")

    return render(request, "academico/anio_lectivo_confirm_delete.html", {
        "obj": anio,
        "nav_active": "academico",
    })

@login_required
def academico_home(request):
    es_directivo_flag = es_directivo(request.user)  # reutilizamos la función de arriba
    return render(request, "academico/homeacademico.html", {
        "nav_active": "academico",
        "es_directivo": es_directivo_flag,
    })

@requiere_gestion
def actividades_list(request, logro_id):
    logro = get_object_or_404(Logro, pk=logro_id)

    actividades = (
        Actividad.objects
        .filter(logro=logro)
        .annotate(total_notas=Count("calificaciones"))
        .order_by("id")
    )

    # 🔍 DEBUG: imprimir en consola
    print("\n===== DEBUG ACTIVIDADES =====")
    for a in actividades:
        print(f"Actividad ID {a.id} | Título: {a.titulo} | total_notas = {a.total_notas}")
    print("===== FIN DEBUG =====\n")

    return render(request, "academico/actividades_list.html", {
        "logro": logro,
        "actividades": actividades,
        "nav_active": "academico",
    })