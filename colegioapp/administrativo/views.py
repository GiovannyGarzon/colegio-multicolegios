from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import *
from .forms import CargoForm, EmpleadoForm, ProveedorForm, ContratoForm, MatriculaForm
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse
from academico.models import Estudiante, AnioLectivo, Matricula, AsignaturaOferta, Periodo, CalificacionLogro, Curso
from django.template.loader import render_to_string
from django.db import transaction
from urllib.parse import urljoin
from django.contrib.auth.decorators import login_required, user_passes_test
import os
from django.conf import settings
from weasyprint import HTML
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from cuentas.models import PerfilUsuario


def home(request):
    return render(request, "administrativo/homeadministrativo.html", {"nav_active": "administrativo"})

def cargos_list(request):
    """
    Vista que lista todos los cargos registrados con filtros y paginación.
    """
    q = (request.GET.get("q") or "").strip()         # búsqueda por nombre o descripción
    activo = request.GET.get("activo", "")           # filtro por estado (1=activo, 0=inactivo)

    # Consulta base
    cargos = Cargo.objects.all().order_by("nombre")

    # Filtro por texto
    if q:
        cargos = cargos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))

    # Filtro por estado
    if activo in ("1", "0"):
        cargos = cargos.filter(activo=(activo == "1"))

    # Paginación (10 por página)
    paginator = Paginator(cargos, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q": q,
        "activo": activo,
        "nav_active": "administrativo",  # para resaltar el menú principal
    }
    return render(request, "administrativo/cargos.html", context)

def empleados_list(request):
    q = (request.GET.get("q") or "").strip()
    cargo_id = request.GET.get("cargo", "")
    activo = request.GET.get("activo", "")

    empleados = Empleado.objects.select_related("cargo").order_by("apellidos", "nombres")

    if q:
        empleados = empleados.filter(
            Q(nombres__icontains=q) | Q(apellidos__icontains=q) | Q(identificacion__icontains=q)
        )

    if cargo_id:
        empleados = empleados.filter(cargo_id=cargo_id)

    if activo in ("1", "0"):
        empleados = empleados.filter(activo=(activo == "1"))

    paginator = Paginator(empleados, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q": q,
        "cargos": Cargo.objects.filter(activo=True).order_by("nombre"),
        "cargo_selected": cargo_id,
        "activo": activo,
        "nav_active": "administrativo",
    }
    return render(request, "administrativo/empleados.html", context)

def proveedores_list(request):
    q = (request.GET.get("q") or "").strip()

    proveedores = Proveedor.objects.all().order_by("nombre")
    if q:
        proveedores = proveedores.filter(Q(nombre__icontains=q) | Q(nit__icontains=q))

    paginator = Paginator(proveedores, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "q": q,
        "nav_active": "administrativo",
    }
    return render(request, "administrativo/proveedores.html", context)

def contratos_list(request):
    q = (request.GET.get("q") or "").strip()
    tipo = (request.GET.get("tipo") or "").strip()
    estado = request.GET.get("estado", "")

    qs = (Contrato.objects
          .select_related("empleado")
          .order_by("-fecha_inicio"))

    if q:
        qs = qs.filter(
            Q(empleado__nombres__icontains=q) |
            Q(empleado__apellidos__icontains=q) |
            Q(empleado__identificacion__icontains=q)
        )

    if tipo:
        qs = qs.filter(tipo_contrato__icontains=tipo)

    if estado in ("vigente", "vencido"):
        hoy = date.today()
        if estado == "vigente":
            qs = qs.filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy))
        else:
            qs = qs.filter(fecha_fin__lt=hoy)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "q": q,
        "tipo": tipo,
        "estado": estado,
        "today": date.today(),        # 👈 se usa en la plantilla
        "nav_active": "administrativo"
    }
    return render(request, "administrativo/contratos.html", context)

def cargo_create(request):
    if request.method == "POST":
        form = CargoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cargo creado correctamente.")
            return redirect(reverse("administrativo:cargos"))
    else:
        form = CargoForm()
    return render(request, "administrativo/cargo_form.html", {
        "form": form,
        "edit_mode": False,
        "nav_active": "administrativo",
    })

def cargo_update(request, pk):
    cargo = get_object_or_404(Cargo, pk=pk)
    if request.method == "POST":
        form = CargoForm(request.POST, instance=cargo)
        if form.is_valid():
            form.save()
            messages.success(request, "Cargo actualizado correctamente.")
            return redirect(reverse("administrativo:cargos"))
    else:
        form = CargoForm(instance=cargo)
    return render(request, "administrativo/cargo_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": cargo,
        "nav_active": "administrativo",
    })

def cargo_delete(request, pk):
    cargo = get_object_or_404(Cargo, pk=pk)
    if request.method == "POST":
        cargo.delete()
        messages.success(request, "Cargo eliminado.")
        return redirect(reverse("administrativo:cargos"))
    return render(request, "administrativo/cargo_confirm_delete.html", {
        "obj": cargo,
        "nav_active": "administrativo",
    })

def empleado_create(request):
    if request.method == "POST":
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Empleado creado correctamente.")
            return redirect(reverse("administrativo:empleados"))
    else:
        form = EmpleadoForm()
    return render(request, "administrativo/empleado_form.html", {
        "form": form,
        "edit_mode": False,
        "nav_active": "administrativo",
    })

def empleado_update(request, pk):
    obj = get_object_or_404(Empleado, pk=pk)
    if request.method == "POST":
        form = EmpleadoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Empleado actualizado correctamente.")
            return redirect(reverse("administrativo:empleados"))
    else:
        form = EmpleadoForm(instance=obj)
    return render(request, "administrativo/empleado_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": obj,
        "nav_active": "administrativo",
    })

def empleado_delete(request, pk):
    obj = get_object_or_404(Empleado, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Empleado eliminado.")
        return redirect(reverse("administrativo:empleados"))
    return render(request, "administrativo/empleado_confirm_delete.html", {
        "obj": obj,
        "nav_active": "administrativo",
    })

def proveedor_create(request):
    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor creado correctamente.")
            return redirect(reverse("administrativo:proveedores"))
    else:
        form = ProveedorForm()

    return render(request, "administrativo/proveedor_form.html", {
        "form": form,
        "edit_mode": False,
        "nav_active": "administrativo",
    })

def proveedor_update(request, pk):
    obj = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        form = ProveedorForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor actualizado correctamente.")
            return redirect(reverse("administrativo:proveedores"))
    else:
        form = ProveedorForm(instance=obj)

    return render(request, "administrativo/proveedor_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": obj,
        "nav_active": "administrativo",
    })

def proveedor_delete(request, pk):
    obj = get_object_or_404(Proveedor, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Proveedor eliminado.")
        return redirect(reverse("administrativo:proveedores"))
    return render(request, "administrativo/proveedor_confirm_delete.html", {
        "obj": obj,
        "nav_active": "administrativo",
    })

def contrato_create(request):
    if request.method == "POST":
        form = ContratoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato creado correctamente.")
            return redirect(reverse("administrativo:contratos"))
    else:
        form = ContratoForm()

    return render(request, "administrativo/contrato_form.html", {
        "form": form,
        "edit_mode": False,
        "nav_active": "administrativo",
    })

def contrato_update(request, pk):
    obj = get_object_or_404(Contrato, pk=pk)
    if request.method == "POST":
        form = ContratoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Contrato actualizado correctamente.")
            return redirect(reverse("administrativo:contratos"))
    else:
        form = ContratoForm(instance=obj)

    return render(request, "administrativo/contrato_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": obj,
        "nav_active": "administrativo",
    })

def contrato_delete(request, pk):
    obj = get_object_or_404(Contrato, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Contrato eliminado.")
        return redirect(reverse("administrativo:contratos"))
    return render(request, "administrativo/contrato_confirm_delete.html", {
        "obj": obj,
        "nav_active": "administrativo",
    })

def certificaciones_buscar(request):
    q = (request.GET.get("q") or "").strip()

    # ✅ filtro por colegio
    estudiantes = Estudiante.objects.filter(school=request.school).order_by("apellidos", "nombres")

    if q:
        estudiantes = estudiantes.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(identificacion__icontains=q)
        )

    if request.method == "POST":
        estudiante_id = request.POST.get("estudiante_id")
        tipo = request.POST.get("tipo")
        anio = request.POST.get("anio")

        url = reverse("administrativo:certificado_pdf", args=[tipo, estudiante_id]) + f"?anio={anio}"
        return redirect(url)

    context = {
        "estudiantes": estudiantes[:20],
        "q": q,
        "nav_active": "administrativo",
        "hoy": date.today(),
    }
    return render(request, "administrativo/certificaciones_buscar.html", context)

def grado_a_letras(grado_raw):
    """
    Convierte un grado numérico ('1','2','3', etc.) a letras.
    Si no se reconoce, devuelve el mismo valor.
    """
    if grado_raw is None:
        return ""

    s = str(grado_raw).strip()
    mapa = {
        "1": "primero",
        "2": "segundo",
        "3": "tercero",
        "4": "cuarto",
        "5": "quinto",
        "6": "sexto",
        "7": "séptimo",
        "8": "octavo",
        "9": "noveno",
        "10": "décimo",
        "11": "undécimo",
    }
    if s.isdigit():
        return mapa.get(s, s)
    # si ya viene en texto tipo "tercero", lo dejamos igual
    return s


def tipo_id_abreviado(estudiante):
    """
    Devuelve R.C. / T.I. / C.C. a partir de estudiante.tipo_documento
    """
    valor = getattr(estudiante, "tipo_documento", "")
    if not valor:
        return ""

    v = str(valor).upper().strip()

    mapa = {
        "RC": "R.C.",
        "TI": "T.I.",
        "CC": "C.C.",
    }
    return mapa.get(v, v)

def promedio_dec(califs):
    """
    Devuelve el promedio de una queryset/lista de CalificacionLogro
    redondeado a 2 decimales. Si no hay calificaciones, devuelve None.
    """
    califs = list(califs)
    if not califs:
        return None

    total = sum((c.nota for c in califs), Decimal("0"))
    prom = total / Decimal(len(califs))
    return prom.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def texto_desempeno(nota):
    """
    Convierte una nota numérica en texto de desempeño.
    """
    if nota is None:
        return ""

    if nota < Decimal("3.0"):
        return "BAJO"
    elif nota < Decimal("4.0"):
        return "BÁSICO"
    elif nota < Decimal("4.6"):
        return "ALTO"
    else:
        return "SUPERIOR"

def _file_url(imagefield):
    if not imagefield:
        return None
    try:
        return "file://" + imagefield.path
    except Exception:
        return None

from academico.models import (
    Estudiante, AnioLectivo, Matricula, AsignaturaOferta,
    CalificacionLogro
)

# -------------------------
# Helper para WeasyPrint
# -------------------------

def file_uri(field):
    """ImageField/FileField -> file:/// URI (Windows + WeasyPrint)."""
    if not field:
        return None
    try:
        return Path(field.path).resolve().as_uri()
    except Exception:
        return None


def _get_rector_por_colegio(school):
    """
    Retorna (nombre, cargo) del rector del colegio actual.
    Identifica por: PerfilUsuario.school = school y user en grupo 'rector'.
    """
    if not school:
        return ("", "RECTOR(A)")

    perfil = (
        PerfilUsuario.objects
        .select_related("user")
        .filter(
            school=school,
            user__groups__name__iexact="rector",
            user__is_active=True,
        )
        .order_by("id")
        .first()
    )

    if not perfil or not perfil.user:
        return ("", "RECTOR(A)")

    nombre = (perfil.user.get_full_name() or perfil.user.username or "").strip()
    return (nombre, "RECTOR(A)")


def grado_a_letras(grado_raw):
    if grado_raw is None:
        return ""
    s = str(grado_raw).strip()
    mapa = {
        "1": "primero", "2": "segundo", "3": "tercero", "4": "cuarto", "5": "quinto",
        "6": "sexto", "7": "séptimo", "8": "octavo", "9": "noveno",
        "10": "décimo", "11": "undécimo",
    }
    return mapa.get(s, s) if s.isdigit() else s


def tipo_id_abreviado(estudiante):
    valor = getattr(estudiante, "tipo_documento", "")
    if not valor:
        return ""
    v = str(valor).upper().strip()
    return {"RC": "R.C.", "TI": "T.I.", "CC": "C.C."}.get(v, v)


def promedio_dec(califs):
    califs = list(califs)
    if not califs:
        return None
    total = sum((c.nota for c in califs), Decimal("0"))
    prom = total / Decimal(len(califs))
    return prom.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def texto_desempeno(nota):
    if nota is None:
        return ""
    if nota < Decimal("3.0"):
        return "BAJO"
    elif nota < Decimal("4.0"):
        return "BÁSICO"
    elif nota < Decimal("4.6"):
        return "ALTO"
    return "SUPERIOR"


def certificado_pdf(request, tipo, estudiante_id):
    # colegio actual (middleware)
    school = getattr(request, "school", None)

    # seguridad multicolegios
    estudiante = get_object_or_404(Estudiante, pk=estudiante_id, school=school)

    # año (?anio=2025)
    anio_param = request.GET.get("anio")
    try:
        anio_num = int(anio_param) if anio_param else date.today().year
    except ValueError:
        anio_num = date.today().year

    anio_obj = AnioLectivo.objects.filter(nombre=str(anio_num)).first()

    # curso / grado por matrícula
    grado_texto = ""
    curso = None
    if anio_obj:
        matricula = (
            Matricula.objects
            .filter(estudiante=estudiante, anio=anio_obj)
            .select_related("curso")
            .first()
        )
        if matricula and matricula.curso:
            grado_texto = matricula.curso.grado
            curso = matricula.curso

    if not grado_texto and getattr(estudiante, "curso", None):
        grado_texto = estudiante.curso.grado
        curso = curso or estudiante.curso

    curso_nombre = str(curso) if curso else ""

    if curso_nombre and "-" in curso_nombre:
        grado_letras = curso_nombre.split("-", 1)[1].strip().lower()
    else:
        grado_letras = grado_a_letras(grado_texto)

    tipo_id = tipo_id_abreviado(estudiante)

    # ✅ LOGO (arriba) = school.logo
    logo_url = file_uri(getattr(school, "logo", None))

    # ✅ MARCA DE AGUA = el MISMO logo
    watermark_url = logo_url

    # ✅ SELLO (al lado de la firma) = school.sello (si está vacío, None)
    sello_url = file_uri(getattr(school, "sello", None))

    rector_nombre, rector_cargo = _get_rector_por_colegio(school)

    context = {
        "school": school,
        "logo_url": logo_url,
        "watermark_url": watermark_url,
        "sello_url": sello_url,  # 👈 nuevo

        "rector_nombre": rector_nombre,
        "rector_cargo": rector_cargo,

        "estudiante": estudiante,
        "anio": anio_num,
        "grado_texto": grado_texto,
        "grado_letras": grado_letras,
        "tipo_id": tipo_id,
        "hoy": date.today(),
        "curso_nombre": curso_nombre,
    }

    if tipo == "estudiantil":
        template_name = "administrativo/certificado_estudiantil.html"
        filename = f"certificado_estudiantil_{estudiante.identificacion}_{anio_num}.pdf"
    elif tipo == "notas":
        template_name = "administrativo/certificado_notas.html"
        filename = f"certificado_notas_{estudiante.identificacion}_{anio_num}.pdf"
        # (tu bloque de notas lo dejas igual)
    else:
        messages.error(request, "Tipo de certificado no válido.")
        return redirect(reverse("administrativo:certificaciones"))

    html_string = render_to_string(template_name, context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf_file = html.write_pdf()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

# -----------------------------
# MATRÍCULAS
# -----------------------------

def matriculas_list(request):
    school = getattr(request, "school", None)

    buscar = (request.GET.get("buscar") or "").strip()
    anio = request.GET.get("anio", "")
    curso = request.GET.get("curso", "")
    estado = request.GET.get("estado", "")  # 1 / 0 / ""

    # ✅ Base: solo matrículas del colegio actual
    matriculas = (
        Matricula.objects
        .select_related("estudiante", "curso", "anio")
        .filter(estudiante__school=school)
        .order_by("-anio__nombre", "curso__grado")
    )

    if buscar:
        matriculas = matriculas.filter(
            Q(estudiante__nombres__icontains=buscar) |
            Q(estudiante__apellidos__icontains=buscar) |
            Q(estudiante__identificacion__icontains=buscar)
        )

    if anio:
        matriculas = matriculas.filter(anio__id=anio)

    if curso:
        matriculas = matriculas.filter(curso__id=curso)

    if estado in ("1", "0"):
        matriculas = matriculas.filter(activo=(estado == "1"))

    # ✅ Idealmente también filtras los combos por school (si aplica)
    anios_qs = AnioLectivo.objects.all().order_by("nombre")
    cursos_qs = Curso.objects.all().order_by("grado", "nombre")

    # Si Curso / AnioLectivo tienen campo school, usa esto en vez de lo anterior:
    # anios_qs = AnioLectivo.objects.filter(school=school).order_by("nombre")
    # cursos_qs = Curso.objects.filter(school=school).order_by("grado", "nombre")

    context = {
        "matriculas": matriculas,
        "anios": anios_qs,
        "cursos": cursos_qs,

        "buscar": buscar,
        "anio_selected": anio,
        "curso_selected": curso,
        "estado_selected": estado,
        "nav_active": "administrativo",
    }
    return render(request, "administrativo/matriculas_list.html", context)


def matricula_create(request):
    school = request.school

    if request.method == "POST":
        form = MatriculaForm(request.POST, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Matrícula creada correctamente.")
            return redirect("administrativo:matriculas")
    else:
        form = MatriculaForm(school=school)

    return render(request, "administrativo/matricula_form.html", {
        "form": form,
        "edit_mode": False,
    })


def matricula_update(request, pk):
    obj = get_object_or_404(Matricula, pk=pk)
    if request.method == "POST":
        form = MatriculaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Matrícula actualizada correctamente.")
            return redirect("administrativo:matriculas")
    else:
        form = MatriculaForm(instance=obj)

    return render(request, "administrativo/matricula_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": obj,  # para mostrar fecha_matricula
    })


def matricula_delete(request, pk):
    matricula = get_object_or_404(Matricula, pk=pk)

    if request.method == "POST":
        matricula.delete()
        messages.success(request, "Matrícula eliminada.")
        return redirect("administrativo:matriculas")

    return render(request, "administrativo/matricula_confirm_delete.html", {
        "obj": matricula,
        "nav_active": "administrativo",
    })

def matriculas_promocionar(request):
    """
    Permite pasar varios estudiantes de un año/curso origen
    a un año/curso destino de forma masiva.
    """
    anios = AnioLectivo.objects.all().order_by("nombre")
    cursos = Curso.objects.all().order_by("grado", "nombre")

    # Para mostrar la lista de estudiantes del curso origen
    matriculas_origen = []

    # ---------- GET: solo filtros y listado ----------
    if request.method == "GET":
        anio_origen_id = request.GET.get("anio_origen")
        curso_origen_id = request.GET.get("curso_origen")

        if anio_origen_id and curso_origen_id:
            matriculas_origen = (
                Matricula.objects
                .select_related("estudiante", "curso", "anio")
                .filter(
                    anio_id=anio_origen_id,
                    curso_id=curso_origen_id,
                    activo=True
                )
                .order_by("estudiante__apellidos", "estudiante__nombres")
            )

        context = {
            "anios": anios,
            "cursos": cursos,
            "matriculas_origen": matriculas_origen,
            "anio_origen_id": anio_origen_id,
            "curso_origen_id": curso_origen_id,
            "nav_active": "administrativo",
        }
        return render(request, "administrativo/matriculas_promocionar.html", context)

    # ---------- POST: crear matrículas destino ----------
    elif request.method == "POST":
        anio_origen_id = request.POST.get("anio_origen")
        curso_origen_id = request.POST.get("curso_origen")
        anio_destino_id = request.POST.get("anio_destino")
        curso_destino_id = request.POST.get("curso_destino")

        seleccionados = request.POST.getlist("estudiantes")  # lista de IDs

        if not (anio_origen_id and curso_origen_id and anio_destino_id and curso_destino_id):
            messages.error(request, "Debes seleccionar año y curso de origen y destino.")
            return redirect("administrativo:matriculas_promocionar")

        if not seleccionados:
            messages.warning(request, "No seleccionaste ningún estudiante.")
            return redirect(
                f"{reverse('administrativo:matriculas_promocionar')}?anio_origen={anio_origen_id}&curso_origen={curso_origen_id}"
            )

        anio_destino = get_object_or_404(AnioLectivo, pk=anio_destino_id)
        curso_destino = get_object_or_404(Curso, pk=curso_destino_id)

        creadas = 0
        saltadas = 0

        with transaction.atomic():
            for est_id in seleccionados:
                est = Estudiante.objects.get(pk=est_id)

                # Si ya tiene matrícula para el año destino, la saltamos
                if Matricula.objects.filter(estudiante=est, anio=anio_destino).exists():
                    saltadas += 1
                    continue

                # Opcional: desactivar matrícula anterior del año origen
                Matricula.objects.filter(
                    estudiante=est,
                    anio_id=anio_origen_id
                ).update(activo=False)

                # Crear matrícula nueva
                Matricula.objects.create(
                    estudiante=est,
                    anio=anio_destino,
                    curso=curso_destino,
                    activo=True,
                )
                creadas += 1

        messages.success(
            request,
            f"Se crearon {creadas} matrículas nuevas. "
            f"Estudiantes ya matriculados en el año destino: {saltadas}."
        )

        return redirect("administrativo:matriculas")

