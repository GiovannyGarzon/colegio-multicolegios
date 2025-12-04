from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, BooleanField, Case, When, Value, Sum, F
from .models import *
from datetime import date, datetime
from django.urls import reverse
from django.contrib import messages
from .forms import AnioEconomicoForm, ConceptoPagoForm, CuentaPorCobrarForm, PagoForm
from urllib.parse import urlencode
from django.db import transaction
from decimal import Decimal
from academico.models import Curso, Estudiante

MESES = [
    (1, "Enero"),
    (2, "Febrero"),
    (3, "Marzo"),
    (4, "Abril"),
    (5, "Mayo"),
    (6, "Junio"),
    (7, "Julio"),
    (8, "Agosto"),
    (9, "Septiembre"),
    (10, "Octubre"),
    (11, "Noviembre"),
    (12, "Diciembre"),
]

def home(request):
    return render(request, "cartera/homecartera.html", {"nav_active": "cartera"})

def cargos_mensuales_selector(request):
    """
    Pantalla para elegir año económico, curso, concepto y mes.
    De aquí se pasa a la planilla con el listado de estudiantes.
    """
    anios = AnioEconomico.objects.all().order_by("-activo", "-nombre")
    cursos = Curso.objects.all().order_by("grado", "nombre")
    conceptos = ConceptoPago.objects.select_related("anio").filter(activo=True).order_by(
        "-anio__activo", "-anio__nombre", "nombre"
    )

    # valores seleccionados (si vienen por GET)
    anio_id = (request.GET.get("anio") or "").strip()
    curso_id = (request.GET.get("curso") or "").strip()
    concepto_id = (request.GET.get("concepto") or "").strip()
    mes = (request.GET.get("mes") or "").strip()

    ctx = {
        "anios": anios,
        "cursos": cursos,
        "conceptos": conceptos,
        "anio_selected": anio_id,
        "curso_selected": curso_id,
        "concepto_selected": concepto_id,
        "mes_selected": mes,
        "nav_active": "cartera",
        "meses": MESES,
    }
    return render(request, "cartera/cargos_mensuales_selector.html", ctx)

def cargos_mensuales_planilla(request):
    """
    Muestra una planilla para un año económico, curso, concepto y mes:
    - GET: solo muestra el listado de estudiantes y si ya tienen la cuenta generada / pagada.
    - POST: genera cuentas por cobrar para los estudiantes seleccionados.
    """
    anio_id = request.GET.get("anio")
    curso_id = request.GET.get("curso")
    concepto_id = request.GET.get("concepto")
    mes_str = request.GET.get("mes")

    if not (anio_id and curso_id and concepto_id and mes_str):
        messages.error(request, "Faltan parámetros. Selecciona año, curso, concepto y mes.")
        return redirect("cartera:cargos_mensuales_selector")

    try:
        mes = int(mes_str)
    except ValueError:
        messages.error(request, "El mes no es válido.")
        return redirect("cartera:cargos_mensuales_selector")

    anio = get_object_or_404(AnioEconomico, pk=anio_id)
    curso = get_object_or_404(Curso, pk=curso_id)
    concepto = get_object_or_404(ConceptoPago, pk=concepto_id, anio=anio)

    # Estudiantes del curso
    estudiantes = Estudiante.objects.filter(curso=curso).order_by("apellidos", "nombres")

    # Cuentas existentes de ese año + concepto + mes
    cuentas_existentes = {
        c.estudiante_id: c
        for c in CuentaPorCobrar.objects.filter(
            estudiante__in=estudiantes,
            concepto=concepto,
            mes=mes
        ).select_related("estudiante")
    }

    # Valor y fecha de vencimiento por defecto
    valor_defecto = concepto.valor
    # ej: vence el día 6 del mes
    fecha_vencimiento_defecto = date(int(anio.nombre), mes, 6)  # asumiendo nombre="2026"

    if request.method == "POST":
        # En el POST vamos a crear cuentas para los estudiantes marcados que NO la tengan.
        creadas = 0
        for est in estudiantes:
            # check en el form: "crear_{{ est.id }}"
            if str(est.id) not in request.POST.getlist("estudiantes"):
                continue

            if est.id in cuentas_existentes:
                # ya tiene cuenta para ese mes/concepto -> nada
                continue

            CuentaPorCobrar.objects.create(
                estudiante=est,
                concepto=concepto,
                fecha_vencimiento=fecha_vencimiento_defecto,
                valor_total=valor_defecto,
                saldo_pendiente=valor_defecto,
                pagada=False,
                mes=mes,
            )
            creadas += 1

        messages.success(request, f"Se generaron {creadas} cargos para {curso} / mes {mes}.")
        # recargar mismo GET para ver la actualización
        url = (
            f"{reverse('cartera:cargos_mensuales_planilla')}"
            f"?anio={anio.id}&curso={curso.id}&concepto={concepto.id}&mes={mes}"
        )
        return redirect(url)

    # Para el GET armamos filas con estado
    filas = []
    for est in estudiantes:
        cta = cuentas_existentes.get(est.id)
        filas.append({
            "estudiante": est,
            "cuenta": cta,
            "estado": (
                "sin_cuenta" if not cta
                else ("pagada" if cta.pagada else "pendiente")
            ),
        })

    ctx = {
        "anio": anio,
        "curso": curso,
        "concepto": concepto,
        "mes": mes,
        "fecha_vencimiento_defecto": fecha_vencimiento_defecto,
        "valor_defecto": valor_defecto,
        "filas": filas,
        "nav_active": "cartera",
    }
    return render(request, "cartera/cargos_mensuales_planilla.html", ctx)

def anios_list(request):
    q = request.GET.get("q", "")
    estado = request.GET.get("estado", "")

    anios = AnioEconomico.objects.all().order_by("-nombre")

    if q:
        anios = anios.filter(Q(nombre__icontains=q))

    if estado == "activo":
        anios = anios.filter(activo=True)
    elif estado == "inactivo":
        anios = anios.filter(activo=False)

    paginator = Paginator(anios, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Para mantener los filtros en la paginación
    querystring = "&".join(
        [f"{key}={value}" for key, value in request.GET.items() if key != "page"]
    )

    return render(
        request,
        "cartera/anioeconomico.html",
        {
            "page_obj": page_obj,
            "q": q,
            "estado": estado,
            "querystring": querystring,
            "nav_active": "cartera",
        },
    )

def conceptos_list(request):
    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio", "")
    recurrente = request.GET.get("recurrente", "")
    activo = request.GET.get("activo", "")

    conceptos = ConceptoPago.objects.select_related("anio").all().order_by("-anio__nombre", "nombre")

    if q:
        conceptos = conceptos.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q)
        )

    if anio_id:
        conceptos = conceptos.filter(anio_id=anio_id)

    if recurrente in ("1", "0"):
        conceptos = conceptos.filter(recurrente=(recurrente == "1"))

    if activo in ("1", "0"):
        conceptos = conceptos.filter(activo=(activo == "1"))

    paginator = Paginator(conceptos, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    querystring = "&".join([
        f"{k}={v}" for k, v in request.GET.items() if k != "page" and v != ""
    ])

    context = {
        "page_obj": page_obj,
        "q": q,
        "anio_selected": anio_id,
        "recurrente": recurrente,
        "activo": activo,
        "anios": AnioEconomico.objects.all().order_by("-nombre"),
        "querystring": querystring,
        "nav_active": "cartera",
    }
    return render(request, "cartera/conceptos.html", context)

def cuentas_list(request):
    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio", "")
    concepto_id = request.GET.get("concepto", "")
    estado = request.GET.get("estado", "")  # pendiente | vencida | pagada | ''
    hoy = date.today()

    qs = (CuentaPorCobrar.objects
          .select_related("estudiante", "concepto", "concepto__anio")
          .all()
          .order_by("-fecha_generacion"))

    # Búsqueda por estudiante (nombres, apellidos, identificación) o concepto
    if q:
        qs = qs.filter(
            Q(estudiante__nombres__icontains=q) |
            Q(estudiante__apellidos__icontains=q) |
            Q(estudiante__identificacion__icontains=q) |
            Q(concepto__nombre__icontains=q)
        )

    # Filtros por año y concepto
    if anio_id:
        qs = qs.filter(concepto__anio_id=anio_id)

    if concepto_id:
        qs = qs.filter(concepto_id=concepto_id)

    # Anotamos si está vencida: (no pagada) y (fecha_vencimiento < hoy)
    qs = qs.annotate(
        es_vencida=Case(
            When(pagada=False, fecha_vencimiento__lt=hoy, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )

    # Filtro por estado
    if estado == "pagada":
        qs = qs.filter(pagada=True)
    elif estado == "pendiente":
        qs = qs.filter(pagada=False, es_vencida=False)
    elif estado == "vencida":
        qs = qs.filter(pagada=False, es_vencida=True)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Mantener filtros en la paginación
    querystring = "&".join(
        [f"{k}={v}" for k, v in request.GET.items() if k != "page" and v != ""]
    )

    # Si el usuario eligió un año, limitamos conceptos a ese año para el select
    if anio_id:
        conceptos = ConceptoPago.objects.select_related("anio").filter(anio_id=anio_id).order_by("nombre")
    else:
        conceptos = ConceptoPago.objects.select_related("anio").all().order_by("-anio__nombre", "nombre")

    context = {
        "page_obj": page_obj,
        "q": q,
        "anios": AnioEconomico.objects.all().order_by("-nombre"),
        "conceptos": conceptos,
        "anio_selected": anio_id,
        "concepto_selected": concepto_id,
        "estado": estado,
        "querystring": querystring,
        "nav_active": "cartera",
    }
    return render(request, "cartera/cuentas.html", context)

def _parse_iso(dstr):
    if not dstr:
        return None
    try:
        return date.fromisoformat(dstr)
    except ValueError:
        return None

def pagos_list(request):
    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio", "")
    concepto_id = request.GET.get("concepto", "")
    medio = (request.GET.get("medio") or "").strip()
    desde = request.GET.get("desde", "")
    hasta = request.GET.get("hasta", "")

    d_from = _parse_iso(desde)
    d_to   = _parse_iso(hasta)

    qs = (Pago.objects
          .select_related(
              "cuenta",
              "cuenta__estudiante",
              "cuenta__concepto",
              "cuenta__concepto__anio",
          )
          .order_by("-fecha_pago", "-id"))

    if q:
        qs = qs.filter(
            Q(cuenta__estudiante__nombres__icontains=q) |
            Q(cuenta__estudiante__apellidos__icontains=q) |
            Q(cuenta__estudiante__identificacion__icontains=q) |
            Q(cuenta__concepto__nombre__icontains=q)
        )

    if anio_id:
        qs = qs.filter(cuenta__concepto__anio_id=anio_id)

    if concepto_id:
        qs = qs.filter(cuenta__concepto_id=concepto_id)

    if medio:
        qs = qs.filter(medio_pago__icontains=medio)

    if d_from:
        qs = qs.filter(fecha_pago__gte=d_from)
    if d_to:
        qs = qs.filter(fecha_pago__lte=d_to)

    # Total filtrado
    total_filtrado = qs.aggregate(total=Sum("valor_pagado"))["total"] or 0

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Mantener filtros en la paginación
    querystring = "&".join(
        [
            f"{k}={v}"
            for k, v in request.GET.items()
            if k != "page" and v not in (None, "", [])
        ]
    )

    # Opciones selects
    if anio_id:
        conceptos = ConceptoPago.objects.select_related("anio").filter(anio_id=anio_id).order_by("nombre")
    else:
        conceptos = ConceptoPago.objects.select_related("anio").all().order_by("-anio__nombre", "nombre")

    context = {
        "page_obj": page_obj,
        "q": q,
        "anios": AnioEconomico.objects.all().order_by("-nombre"),
        "conceptos": conceptos,
        "anio_selected": anio_id,
        "concepto_selected": concepto_id,
        "medio": medio,
        "desde": desde,
        "hasta": hasta,
        "total_filtrado": total_filtrado,
        "querystring": querystring,
        "nav_active": "cartera",
    }
    return render(request, "cartera/pagos.html", context)

def reportes_home(request):
    return render(request, "cartera/reportes.html", {"nav_active": "cartera"})

def reporte_pagos_por_anio(request):
    # Totales por año
    totales_anio = (
        Pago.objects
        .values(anio=F("cuenta__concepto__anio__nombre"))
        .annotate(total=Sum("valor_pagado"))
        .order_by("-anio")
    )
    # Totales por año y concepto
    totales_anio_concepto = (
        Pago.objects
        .values(
            anio=F("cuenta__concepto__anio__nombre"),
            concepto=F("cuenta__concepto__nombre")
        )
        .annotate(total=Sum("valor_pagado"))
        .order_by("-anio", "concepto")
    )
    ctx = {
        "totales_anio": totales_anio,
        "totales_anio_concepto": totales_anio_concepto,
        "nav_active": "cartera",
    }
    return render(request, "cartera/reportes_pagos_anio.html", ctx)

def reporte_pendientes(request):
    hoy = date.today()
    pendientes = (
        CuentaPorCobrar.objects
        .select_related("estudiante", "concepto", "concepto__anio")
        .filter(pagada=False)
        .order_by("estudiante__apellidos", "estudiante__nombres")
    )
    ctx = {"pendientes": pendientes, "hoy": hoy, "nav_active": "cartera"}
    return render(request, "cartera/reportes_pendientes.html", ctx)

def reporte_medios_pago(request):
    resumen = (
        Pago.objects
        .values("medio_pago")
        .annotate(total=Sum("valor_pagado"))
        .order_by("medio_pago")
    )
    ctx = {"resumen": resumen, "nav_active": "cartera"}
    return render(request, "cartera/reportes_medios_pago.html", ctx)

def reporte_morosos(request):
    # Morosos: cuentas no pagadas con saldo > 0
    morosos = (
        CuentaPorCobrar.objects
        .select_related("estudiante", "concepto", "concepto__anio")
        .filter(pagada=False)
        .order_by("estudiante__apellidos", "estudiante__nombres")
    )
    # Total global de saldos pendientes
    total_pendiente = morosos.aggregate(total=Sum("saldo_pendiente"))["total"] or 0
    ctx = {
        "morosos": morosos,
        "total_pendiente": total_pendiente,
        "nav_active": "cartera",
    }
    return render(request, "cartera/reportes_morosos.html", ctx)

def anios_list(request):
    q = (request.GET.get("q") or "").strip()
    estado = request.GET.get("estado", "")

    qs = AnioEconomico.objects.all().order_by("-activo", "-nombre")

    if q:
        qs = qs.filter(Q(nombre__icontains=q))

    if estado in ("activo", "inactivo"):
        qs = qs.filter(activo=(estado == "activo"))

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # conservar filtros en paginación
    params = request.GET.copy()
    params.pop("page", None)
    from urllib.parse import urlencode
    querystring = urlencode(params)

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "estado": estado,
        "querystring": querystring,
        "nav_active": "cartera",
    }
    return render(request, "cartera/anoeconomico.html", ctx)

def anio_create(request):
    if request.method == "POST":
        form = AnioEconomicoForm(request.POST)
        if form.is_valid():
            obj = form.save()
            # Si se marca activo, desactivar los demás
            if obj.activo:
                AnioEconomico.objects.exclude(pk=obj.pk).update(activo=False)
            messages.success(request, "Año económico creado correctamente.")
            return redirect(reverse("cartera:anios"))
    else:
        form = AnioEconomicoForm()

    return render(request, "cartera/anio_form.html", {
        "form": form,
        "edit_mode": False,
        "nav_active": "cartera",
    })

def anio_update(request, pk):
    obj = get_object_or_404(AnioEconomico, pk=pk)
    if request.method == "POST":
        form = AnioEconomicoForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            if obj.activo:
                AnioEconomico.objects.exclude(pk=obj.pk).update(activo=False)
            messages.success(request, "Año económico actualizado correctamente.")
            return redirect(reverse("cartera:anios"))
    else:
        form = AnioEconomicoForm(instance=obj)

    return render(request, "cartera/anio_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": obj,
        "nav_active": "cartera",
    })

def anio_delete(request, pk):
    obj = get_object_or_404(AnioEconomico, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Año económico eliminado.")
        return redirect(reverse("cartera:anios"))
    return render(request, "cartera/anio_confirm_delete.html", {
        "obj": obj,
        "nav_active": "cartera",
    })

def anio_set_activo(request, pk):
    """
    Marca un año como activo y desactiva los demás.
    Úsalo desde la lista para activar rápidamente.
    """
    obj = get_object_or_404(AnioEconomico, pk=pk)
    AnioEconomico.objects.update(activo=False)
    obj.activo = True
    obj.save(update_fields=["activo"])
    messages.success(request, f"Se activó el año económico {obj.nombre}.")
    return redirect(reverse("cartera:anios"))

def conceptos_list(request):
    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio") or ""
    recurrente = request.GET.get("recurrente") or ""
    activo = request.GET.get("activo") or ""

    conceptos = ConceptoPago.objects.select_related("anio").all().order_by("-anio__activo", "-anio__nombre", "nombre")

    if q:
        conceptos = conceptos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q) | Q(anio__nombre__icontains=q))
    if anio_id:
        conceptos = conceptos.filter(anio_id=anio_id)
    if recurrente in ("1", "0"):
        conceptos = conceptos.filter(recurrente=(recurrente == "1"))
    if activo in ("1", "0"):
        conceptos = conceptos.filter(activo=(activo == "1"))

    paginator = Paginator(conceptos, 12)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    params = request.GET.copy()
    params.pop("page", None)
    querystring = urlencode(params)

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "anio_selected": anio_id,
        "recurrente": recurrente,
        "activo": activo,
        "anios": AnioEconomico.objects.all().order_by("-activo", "-nombre"),
        "querystring": querystring,
        "nav_active": "cartera",
    }
    return render(request, "cartera/conceptos.html", ctx)

def concepto_create(request):
    if request.method == "POST":
        form = ConceptoPagoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Concepto creado correctamente.")
            return redirect("cartera:conceptos")
    else:
        form = ConceptoPagoForm()
    return render(request, "cartera/concepto_form.html", {"form": form, "edit_mode": False, "nav_active": "cartera"})

def concepto_update(request, pk):
    obj = get_object_or_404(ConceptoPago, pk=pk)
    if request.method == "POST":
        form = ConceptoPagoForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Concepto actualizado correctamente.")
            return redirect("cartera:conceptos")
    else:
        form = ConceptoPagoForm(instance=obj)
    return render(request, "cartera/concepto_form.html", {"form": form, "edit_mode": True, "obj": obj, "nav_active": "cartera"})

def concepto_delete(request, pk):
    obj = get_object_or_404(ConceptoPago, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Concepto eliminado.")
        return redirect("cartera:conceptos")
    return render(request, "cartera/concepto_confirm_delete.html", {"obj": obj, "nav_active": "cartera"})

def cuentas_list(request):
    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio") or ""
    curso_id = request.GET.get("curso") or ""
    concepto_id = request.GET.get("concepto") or ""
    estado = request.GET.get("estado") or ""   # "pendiente" | "pagada" | "vencida"

    qs = (CuentaPorCobrar.objects
          .select_related("estudiante", "estudiante__curso", "concepto", "concepto__anio")
          .order_by("-fecha_generacion", "estudiante__apellidos"))

    if q:
        qs = qs.filter(
            Q(estudiante__nombres__icontains=q) |
            Q(estudiante__apellidos__icontains=q) |
            Q(estudiante__identificacion__icontains=q) |
            Q(concepto__nombre__icontains=q)
        )
    if anio_id:
        qs = qs.filter(concepto__anio_id=anio_id)
    if curso_id:
        qs = qs.filter(estudiante__curso_id=curso_id)
    if concepto_id:
        qs = qs.filter(concepto_id=concepto_id)

    hoy = date.today()
    if estado == "pendiente":
        qs = qs.filter(pagada=False, saldo_pendiente__gt=0)
    elif estado == "pagada":
        qs = qs.filter(pagada=True, saldo_pendiente=0)
    elif estado == "vencida":
        qs = qs.filter(pagada=False, fecha_vencimiento__lt=hoy, saldo_pendiente__gt=0)

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    # combos
    from academico.models import Curso
    ctx = {
        "page_obj": page_obj,
        "q": q,
        "anio_selected": anio_id,
        "curso_selected": curso_id,
        "concepto_selected": concepto_id,
        "estado": estado,
        "anios": AnioEconomico.objects.all().order_by("-activo", "-nombre"),
        "cursos": Curso.objects.all().order_by("grado", "nombre"),
        "conceptos": ConceptoPago.objects.select_related("anio").order_by("-anio__activo", "-anio__nombre", "nombre"),
        "hoy": hoy,
        "nav_active": "cartera",
    }
    return render(request, "cartera/cuentas.html", ctx)

def cuenta_create(request):
    if request.method == "POST":
        form = CuentaPorCobrarForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Cuenta por cobrar creada.")
            return redirect("cartera:cuentas")
    else:
        form = CuentaPorCobrarForm()
    return render(request, "cartera/cuenta_form.html", {"form": form, "edit_mode": False, "nav_active": "cartera"})

def cuenta_update(request, pk):
    obj = get_object_or_404(CuentaPorCobrar, pk=pk)
    if request.method == "POST":
        form = CuentaPorCobrarForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Cuenta actualizada.")
            return redirect("cartera:cuentas")
    else:
        form = CuentaPorCobrarForm(instance=obj)
    return render(request, "cartera/cuenta_form.html", {"form": form, "edit_mode": True, "obj": obj, "nav_active": "cartera"})

def cuenta_delete(request, pk):
    obj = get_object_or_404(CuentaPorCobrar, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Cuenta eliminada.")
        return redirect("cartera:cuentas")
    return render(request, "cartera/cuenta_confirm_delete.html", {"obj": obj, "nav_active": "cartera"})

def pago_create(request):
    if request.method == "POST":
        form = PagoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                pago = form.save(commit=False)
                cuenta = pago.cuenta
                # Validación ya se hizo en el form; aquí actualizamos la cuenta
                cuenta.saldo_pendiente = (cuenta.saldo_pendiente or Decimal("0")) - (pago.valor_pagado or Decimal("0"))
                if cuenta.saldo_pendiente <= 0:
                    cuenta.saldo_pendiente = Decimal("0")
                    cuenta.pagada = True
                cuenta.save(update_fields=["saldo_pendiente", "pagada"])
                pago.save()
            messages.success(request, "Pago registrado correctamente.")
            return redirect("cartera:pagos")
    else:
        form = PagoForm()
    return render(request, "cartera/pago_form.html", {"form": form, "edit_mode": False, "nav_active": "cartera"})

# ---------- PAGOS: UPDATE ----------
def pago_update(request, pk):
    obj = get_object_or_404(Pago, pk=pk)
    if request.method == "POST":
        form = PagoForm(request.POST, instance=obj)
        if form.is_valid():
            with transaction.atomic():
                original = Pago.objects.select_related("cuenta").get(pk=obj.pk)
                pago = form.save(commit=False)
                cuenta = pago.cuenta
                delta = (pago.valor_pagado or Decimal("0")) - (original.valor_pagado or Decimal("0"))
                # Ajustar saldo con delta (ya validado en form)
                cuenta.saldo_pendiente = (cuenta.saldo_pendiente or Decimal("0")) - delta
                if cuenta.saldo_pendiente <= 0:
                    cuenta.saldo_pendiente = Decimal("0")
                    cuenta.pagada = True
                else:
                    cuenta.pagada = False
                cuenta.save(update_fields=["saldo_pendiente", "pagada"])
                pago.save()
            messages.success(request, "Pago actualizado correctamente.")
            return redirect("cartera:pagos")
    else:
        form = PagoForm(instance=obj)
    return render(request, "cartera/pago_form.html", {"form": form, "edit_mode": True, "obj": obj, "nav_active": "cartera"})

# ---------- PAGOS: DELETE ----------
def pago_delete(request, pk):
    obj = get_object_or_404(Pago, pk=pk)
    if request.method == "POST":
        with transaction.atomic():
            cuenta = obj.cuenta
            # Revertir el pago en la cuenta
            cuenta.saldo_pendiente = (cuenta.saldo_pendiente or Decimal("0")) + (obj.valor_pagado or Decimal("0"))
            if cuenta.saldo_pendiente > 0:
                cuenta.pagada = False
            cuenta.save(update_fields=["saldo_pendiente", "pagada"])
            obj.delete()
        messages.success(request, "Pago eliminado.")
        return redirect("cartera:pagos")
    return render(request, "cartera/pago_confirm_delete.html", {"obj": obj, "nav_active": "cartera"})