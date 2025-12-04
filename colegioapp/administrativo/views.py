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
from django.contrib.auth.decorators import login_required, user_passes_test
import os
from django.conf import settings
from weasyprint import HTML
from decimal import Decimal, ROUND_HALF_UP

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
    estudiantes = Estudiante.objects.all().order_by("apellidos", "nombres")

    if q:
        estudiantes = estudiantes.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(identificacion__icontains=q)
        )

    # Cuando el usuario selecciona un estudiante y tipo y envía el formulario
    if request.method == "POST":
        estudiante_id = request.POST.get("estudiante_id")
        tipo = request.POST.get("tipo")  # "estudiantil" o "notas"
        anio = request.POST.get("anio")
        # podrías validar aquí

        url = reverse(
            "administrativo:certificado_pdf",
            args=[tipo, estudiante_id]
        ) + f"?anio={anio}"
        return redirect(url)

    context = {
        "estudiantes": estudiantes[:20],  # puedes paginar luego
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

def certificado_pdf(request, tipo, estudiante_id):
    # 1. Estudiante
    estudiante = get_object_or_404(Estudiante, pk=estudiante_id)

    # 2. Año solicitado (?anio=2025). Si no llega, usa el año actual.
    anio_param = request.GET.get("anio")
    try:
        anio_num = int(anio_param) if anio_param else date.today().year
    except ValueError:
        anio_num = date.today().year

    # 3. Año lectivo
    anio_obj = AnioLectivo.objects.filter(nombre=str(anio_num)).first()

    # 4. Resolver el grado de ese año usando Matricula
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

    # 5. Si no hay matrícula para ese año, usamos el curso actual como respaldo
    if not grado_texto and hasattr(estudiante, "curso") and estudiante.curso:
        grado_texto = estudiante.curso.grado
        if not curso:
            curso = estudiante.curso

    # Texto del curso tal cual (ej: "201 - SEGUNDO")
    curso_nombre = str(curso) if curso else ""

    # Grado en letras: si el curso viene "201 - SEGUNDO", usamos "segundo"
    if curso_nombre and "-" in curso_nombre:
        grado_letras = curso_nombre.split("-", 1)[1].strip().lower()
    else:
        grado_letras = grado_a_letras(grado_texto)

    # Tipo de identificación abreviado
    tipo_id = tipo_id_abreviado(estudiante)

    # 6. Contexto común
    context = {
        "estudiante": estudiante,
        "anio": anio_num,
        "grado_texto": grado_texto,
        "grado_letras": grado_letras,
        "tipo_id": tipo_id,
        "hoy": date.today(),
        "curso_nombre": curso_nombre,
    }

    # 7. Elegir plantilla y nombre de archivo según tipo
    if tipo == "estudiantil":
        template_name = "administrativo/certificado_estudiantil.html"
        filename = f"certificado_estudiantil_{estudiante.identificacion}_{anio_num}.pdf"

    elif tipo == "notas":
        template_name = "administrativo/certificado_notas.html"
        filename = f"certificado_notas_{estudiante.identificacion}_{anio_num}.pdf"

        # ===================== CARGAR NOTAS =====================
        notas_resumen = []
        prom_general = None
        aprobacion_texto = ""

        if anio_obj and curso:
            ofertas = (
                AsignaturaOferta.objects
                .filter(anio=anio_obj, curso=curso)
                .select_related("asignatura")
            )

            for oferta in ofertas:
                fila = {
                    "area": oferta.asignatura.nombre,
                    "ih": oferta.intensidad_horaria,
                    "p1": "",
                    "p2": "",
                    "p3": "",
                    "final": "",
                    "desempeno": "",
                }

                # Promedio por periodo
                for numero, clave in [(1, "p1"), (2, "p2"), (3, "p3")]:
                    califs_p = CalificacionLogro.objects.filter(
                        estudiante=estudiante,
                        logro__oferta=oferta,
                        logro__periodo__numero=numero,
                        logro__periodo__anio=anio_obj,
                    )
                    prom_p = promedio_dec(califs_p)
                    fila[clave] = f"{prom_p:.2f}" if prom_p is not None else ""

                # Promedio final de toda la asignatura
                califs_todas = CalificacionLogro.objects.filter(
                    estudiante=estudiante,
                    logro__oferta=oferta,
                    logro__periodo__anio=anio_obj,
                )
                prom_final = promedio_dec(califs_todas)
                if prom_final is not None:
                    fila["final"] = f"{prom_final:.2f}"
                    fila["desempeno"] = texto_desempeno(prom_final)

                notas_resumen.append(fila)

            # Promedio general del año
            califs_anio = CalificacionLogro.objects.filter(
                estudiante=estudiante,
                logro__periodo__anio=anio_obj,
            )
            prom_general = promedio_dec(califs_anio)

            if prom_general is not None:
                aprobacion_texto = "APROBÓ" if prom_general > Decimal("3.0") else "NO APROBÓ"

        context["notas"] = notas_resumen
        context["prom_general"] = prom_general
        context["aprobacion_texto"] = aprobacion_texto
        # ========================================================

    else:
        messages.error(request, "Tipo de certificado no válido.")
        return redirect("administrativo:certificaciones")

    # 8. Renderizar HTML y convertir a PDF con WeasyPrint
    html_string = render_to_string(template_name, context)
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf_file = html.write_pdf()

    # 9. Respuesta HTTP con el PDF
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename=\"{filename}\"'
    return response

# -----------------------------
# MATRÍCULAS
# -----------------------------

def matriculas_list(request):
    q = (request.GET.get("q") or "").strip()
    anio = request.GET.get("anio", "")
    curso = request.GET.get("curso", "")

    matriculas = Matricula.objects.select_related("estudiante", "curso", "anio") \
                                  .order_by("-anio__nombre", "curso__grado")

    if q:
        matriculas = matriculas.filter(
            Q(estudiante__nombres__icontains=q) |
            Q(estudiante__apellidos__icontains=q) |
            Q(estudiante__identificacion__icontains=q)
        )

    if anio:
        matriculas = matriculas.filter(anio__id=anio)

    if curso:
        matriculas = matriculas.filter(curso__id=curso)

    context = {
        "matriculas": matriculas,
        "anios": AnioLectivo.objects.all(),
        "cursos": Curso.objects.all(),
        "q": q,
        "anio_selected": anio,
        "curso_selected": curso,
        "nav_active": "administrativo",
    }
    return render(request, "administrativo/matriculas_list.html", context)


def matricula_create(request):
    if request.method == "POST":
        form = MatriculaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Matrícula creada correctamente.")
            return redirect("administrativo:matriculas")
    else:
        form = MatriculaForm()

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

