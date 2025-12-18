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
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    # ✅ SOLO DATOS DEL COLEGIO
    anios = AnioEconomico.objects.filter(school=school).order_by("-activo", "-nombre")
    cursos = Curso.objects.filter(school=school).order_by("grado", "nombre")
    conceptos = (
        ConceptoPago.objects
        .select_related("anio")
        .filter(school=school, activo=True)  # ✅ SOLO DEL COLEGIO
        .order_by("-anio__activo", "-anio__nombre", "nombre")
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
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    anio_id = (request.GET.get("anio") or "").strip()
    curso_id = (request.GET.get("curso") or "").strip()
    concepto_id = (request.GET.get("concepto") or "").strip()
    mes_str = (request.GET.get("mes") or "").strip()

    if not (anio_id and curso_id and concepto_id and mes_str):
        messages.error(request, "Faltan parámetros. Selecciona año, curso, concepto y mes.")
        return redirect("cartera:cargos_mensuales_selector")

    try:
        mes = int(mes_str)
        if mes < 1 or mes > 12:
            raise ValueError()
    except ValueError:
        messages.error(request, "El mes no es válido.")
        return redirect("cartera:cargos_mensuales_selector")

    # ✅ SOLO DEL COLEGIO
    anio = get_object_or_404(AnioEconomico, pk=anio_id, school=school)
    curso = get_object_or_404(Curso, pk=curso_id, school=school)
    concepto = get_object_or_404(ConceptoPago, pk=concepto_id, anio=anio, school=school)

    # ✅ Estudiantes SOLO del colegio + curso
    estudiantes = (
        Estudiante.objects
        .filter(school=school, curso=curso)
        .order_by("apellidos", "nombres")
    )

    # ✅ Cuentas existentes SOLO de esos estudiantes + ese concepto + mes
    cuentas_existentes = {
        c.estudiante_id: c
        for c in (
            CuentaPorCobrar.objects
            .filter(estudiante__in=estudiantes, concepto=concepto, mes=mes)
            .select_related("estudiante")
        )
    }

    # Valor y fecha de vencimiento por defecto
    valor_defecto = concepto.valor or Decimal("0")

    # Si anio.nombre es "2026" (string), esto funciona:
    try:
        anio_num = int(str(anio.nombre))
    except ValueError:
        anio_num = date.today().year  # fallback seguro

    # Ej: vence el día 6 del mes
    fecha_vencimiento_defecto = date(anio_num, mes, 6)

    if request.method == "POST":
        seleccionados = set(request.POST.getlist("estudiantes"))  # ids como strings
        creadas = 0

        for est in estudiantes:
            if str(est.id) not in seleccionados:
                continue

            if est.id in cuentas_existentes:
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
        url = (
            f"{reverse('cartera:cargos_mensuales_planilla')}"
            f"?anio={anio.id}&curso={curso.id}&concepto={concepto.id}&mes={mes}"
        )
        return redirect(url)

    # GET: armamos filas con estado
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


def conceptos_list(request):
    school = getattr(request, "school", None)

    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio") or ""
    recurrente = request.GET.get("recurrente") or ""
    activo = request.GET.get("activo") or ""

    conceptos = (
        ConceptoPago.objects
        .select_related("anio")
        .filter(school=school)  # ✅ SOLO DEL COLEGIO
        .order_by("-anio__activo", "-anio__nombre", "nombre")
    )

    if q:
        conceptos = conceptos.filter(
            Q(nombre__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(anio__nombre__icontains=q)
        )

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
        "anios": AnioEconomico.objects.filter(school=school).order_by("-activo", "-nombre"),  # ✅
        "querystring": querystring,
        "nav_active": "cartera",
    }
    return render(request, "cartera/conceptos.html", ctx)

def cuentas_list(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio", "")
    concepto_id = request.GET.get("concepto", "")
    estado = request.GET.get("estado", "")
    hoy = date.today()

    qs = (
        CuentaPorCobrar.objects
        .select_related("estudiante", "concepto", "concepto__anio")
        .filter(concepto__school=school)   # ✅ clave
        .order_by("-fecha_generacion")
    )

    if q:
        qs = qs.filter(
            Q(estudiante__nombres__icontains=q) |
            Q(estudiante__apellidos__icontains=q) |
            Q(estudiante__identificacion__icontains=q) |
            Q(concepto__nombre__icontains=q)
        )

    if anio_id:
        qs = qs.filter(concepto__anio_id=anio_id)

    if concepto_id:
        qs = qs.filter(concepto_id=concepto_id)

    qs = qs.annotate(
        es_vencida=Case(
            When(pagada=False, fecha_vencimiento__lt=hoy, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )

    if estado == "pagada":
        qs = qs.filter(pagada=True)
    elif estado == "pendiente":
        qs = qs.filter(pagada=False, es_vencida=False)
    elif estado == "vencida":
        qs = qs.filter(pagada=False, es_vencida=True)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    querystring = "&".join([f"{k}={v}" for k, v in request.GET.items() if k != "page" and v != ""])

    # selects SOLO del colegio
    anios = AnioEconomico.objects.filter(school=school).order_by("-activo", "-nombre")
    if anio_id:
        conceptos = ConceptoPago.objects.filter(school=school, anio_id=anio_id).order_by("nombre")
    else:
        conceptos = ConceptoPago.objects.filter(school=school).select_related("anio").order_by("-anio__nombre", "nombre")

    context = {
        "page_obj": page_obj,
        "q": q,
        "anios": anios,
        "conceptos": conceptos,
        "anio_selected": anio_id,
        "concepto_selected": concepto_id,
        "estado": estado,
        "querystring": querystring,
        "hoy": hoy,
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
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    q = (request.GET.get("q") or "").strip()
    anio_id = request.GET.get("anio", "")
    concepto_id = request.GET.get("concepto", "")
    medio = (request.GET.get("medio") or "").strip()
    desde = request.GET.get("desde", "")
    hasta = request.GET.get("hasta", "")

    d_from = _parse_iso(desde)
    d_to = _parse_iso(hasta)

    qs = (
        Pago.objects
        .select_related("cuenta", "cuenta__estudiante", "cuenta__concepto", "cuenta__concepto__anio")
        .filter(cuenta__concepto__school=school)  # ✅ clave
        .order_by("-fecha_pago", "-id")
    )

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

    total_filtrado = qs.aggregate(total=Sum("valor_pagado"))["total"] or 0

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    querystring = "&".join(
        [f"{k}={v}" for k, v in request.GET.items() if k != "page" and v not in (None, "", [])]
    )

    anios = AnioEconomico.objects.filter(school=school).order_by("-activo", "-nombre")
    if anio_id:
        conceptos = ConceptoPago.objects.filter(school=school, anio_id=anio_id).order_by("nombre")
    else:
        conceptos = ConceptoPago.objects.filter(school=school).select_related("anio").order_by("-anio__nombre", "nombre")

    context = {
        "page_obj": page_obj,
        "q": q,
        "anios": anios,
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
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    return render(request, "cartera/reportes.html", {"nav_active": "cartera"})

def reporte_pagos_por_anio(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    # ✅ Solo pagos del colegio
    qs = Pago.objects.filter(cuenta__concepto__school=school)

    # Totales por año
    totales_anio = (
        qs.values(anio=F("cuenta__concepto__anio__nombre"))
          .annotate(total=Sum("valor_pagado"))
          .order_by("-anio")
    )

    # Totales por año y concepto
    totales_anio_concepto = (
        qs.values(
            anio=F("cuenta__concepto__anio__nombre"),
            concepto=F("cuenta__concepto__nombre"),
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
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    hoy = date.today()

    # ✅ Solo cuentas del colegio (pendientes)
    pendientes = (
        CuentaPorCobrar.objects
        .select_related("estudiante", "concepto", "concepto__anio")
        .filter(concepto__school=school, pagada=False)
        .order_by("estudiante__apellidos", "estudiante__nombres")
    )

    ctx = {"pendientes": pendientes, "hoy": hoy, "nav_active": "cartera"}
    return render(request, "cartera/reportes_pendientes.html", ctx)

def reporte_medios_pago(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    # ✅ Solo pagos del colegio
    resumen = (
        Pago.objects
        .filter(cuenta__concepto__school=school)
        .values("medio_pago")
        .annotate(total=Sum("valor_pagado"))
        .order_by("medio_pago")
    )

    ctx = {"resumen": resumen, "nav_active": "cartera"}
    return render(request, "cartera/reportes_medios_pago.html", ctx)

def reporte_morosos(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    # ✅ Morosos: cuentas NO pagadas con saldo > 0 (solo del colegio)
    morosos = (
        CuentaPorCobrar.objects
        .select_related("estudiante", "concepto", "concepto__anio")
        .filter(concepto__school=school, pagada=False, saldo_pendiente__gt=0)
        .order_by("estudiante__apellidos", "estudiante__nombres")
    )

    total_pendiente = morosos.aggregate(total=Sum("saldo_pendiente"))["total"] or 0

    ctx = {
        "morosos": morosos,
        "total_pendiente": total_pendiente,
        "nav_active": "cartera",
    }
    return render(request, "cartera/reportes_morosos.html", ctx)

def anios_list(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:home")

    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()

    qs = AnioEconomico.objects.filter(school=school).order_by("-activo", "-nombre")

    if q:
        qs = qs.filter(nombre__icontains=q)

    if estado in ("activo", "inactivo"):
        qs = qs.filter(activo=(estado == "activo"))

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    querystring = urlencode(params)

    return render(request, "cartera/anoeconomico.html", {
        "page_obj": page_obj,
        "q": q,
        "estado": estado,
        "querystring": querystring,
        "nav_active": "cartera",
    })

def anio_create(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:anios")

    if request.method == "POST":
        form = AnioEconomicoForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.school = school
            obj.save()

            # Si se marca activo, desactivar los demás PERO SOLO DE ESTE COLEGIO
            if obj.activo:
                AnioEconomico.objects.filter(school=school).exclude(pk=obj.pk).update(activo=False)

            messages.success(request, "Año económico creado correctamente.")
            return redirect("cartera:anios")
    else:
        form = AnioEconomicoForm()

    return render(request, "cartera/anio_form.html", {
        "form": form,
        "edit_mode": False,
        "nav_active": "cartera",
    })

def anio_update(request, pk):
    school = getattr(request, "school", None)
    obj = get_object_or_404(AnioEconomico, pk=pk, school=school)

    if request.method == "POST":
        form = AnioEconomicoForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.school = school
            updated.save()

            if updated.activo:
                AnioEconomico.objects.filter(school=school).exclude(pk=updated.pk).update(activo=False)

            messages.success(request, "Año económico actualizado correctamente.")
            return redirect("cartera:anios")
    else:
        form = AnioEconomicoForm(instance=obj)

    return render(request, "cartera/anio_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": obj,
        "nav_active": "cartera",
    })

def anio_delete(request, pk):
    school = getattr(request, "school", None)
    obj = get_object_or_404(AnioEconomico, pk=pk, school=school)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Año económico eliminado.")
        return redirect(reverse("cartera:anios"))
    return render(request, "cartera/anio_confirm_delete.html", {
        "obj": obj,
        "nav_active": "cartera",
    })

def anio_set_activo(request, pk):
    school = getattr(request, "school", None)
    obj = get_object_or_404(AnioEconomico, pk=pk, school=school)

    AnioEconomico.objects.filter(school=school).update(activo=False)
    obj.activo = True
    obj.save(update_fields=["activo"])

    messages.success(request, f"Se activó el año económico {obj.nombre}.")
    return redirect("cartera:anios")

def concepto_create(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:conceptos")

    if request.method == "POST":
        form = ConceptoPagoForm(request.POST, school=school)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.school = school
            obj.save()
            messages.success(request, "Concepto creado correctamente.")
            return redirect("cartera:conceptos")
    else:
        form = ConceptoPagoForm(school=school)

    return render(request, "cartera/concepto_form.html", {
        "form": form,
        "edit_mode": False,
        "nav_active": "cartera"
    })

def concepto_update(request, pk):
    school = getattr(request, "school", None)

    obj = get_object_or_404(ConceptoPago, pk=pk, school=school)  # 🔒

    if request.method == "POST":
        form = ConceptoPagoForm(request.POST or None, instance=obj, school=school)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.school = school  # 🔒 por seguridad
            updated.save()
            messages.success(request, "Concepto actualizado correctamente.")
            return redirect("cartera:conceptos")
    else:
        form = ConceptoPagoForm(instance=obj, school=school)

    return render(request, "cartera/concepto_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": obj,
        "nav_active": "cartera"
    })

def concepto_delete(request, pk):
    obj = get_object_or_404(ConceptoPago, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Concepto eliminado.")
        return redirect("cartera:conceptos")
    return render(request, "cartera/concepto_confirm_delete.html", {"obj": obj, "nav_active": "cartera"})



def cuenta_create(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:cuentas")

    if request.method == "POST":
        form = CuentaPorCobrarForm(request.POST, school=school)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Cuenta por cobrar creada.")
            return redirect("cartera:cuentas")
    else:
        form = CuentaPorCobrarForm(school=school)

    return render(request, "cartera/cuenta_form.html", {
        "form": form,
        "edit_mode": False,
        "nav_active": "cartera",
    })


def cuenta_update(request, pk):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:cuentas")

    obj = get_object_or_404(CuentaPorCobrar, pk=pk, concepto__school=school)  # ✅

    if request.method == "POST":
        form = CuentaPorCobrarForm(request.POST, instance=obj, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta actualizada.")
            return redirect("cartera:cuentas")
    else:
        form = CuentaPorCobrarForm(instance=obj, school=school)

    return render(request, "cartera/cuenta_form.html", {
        "form": form,
        "edit_mode": True,
        "obj": obj,
        "nav_active": "cartera",
    })


def cuenta_delete(request, pk):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:cuentas")

    obj = get_object_or_404(CuentaPorCobrar, pk=pk, concepto__school=school)  # ✅

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Cuenta eliminada.")
        return redirect("cartera:cuentas")

    return render(request, "cartera/cuenta_confirm_delete.html", {
        "obj": obj,
        "nav_active": "cartera",
    })


def pago_create(request):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:pagos")

    if request.method == "POST":
        form = PagoForm(request.POST, school=school)
        if form.is_valid():
            with transaction.atomic():
                pago = form.save(commit=False)
                cuenta = pago.cuenta

                cuenta.saldo_pendiente = (cuenta.saldo_pendiente or Decimal("0")) - (pago.valor_pagado or Decimal("0"))
                if cuenta.saldo_pendiente <= 0:
                    cuenta.saldo_pendiente = Decimal("0")
                    cuenta.pagada = True
                cuenta.save(update_fields=["saldo_pendiente", "pagada"])
                pago.save()

            messages.success(request, "Pago registrado correctamente.")
            return redirect("cartera:pagos")
    else:
        form = PagoForm(school=school)

    return render(request, "cartera/pago_form.html", {"form": form, "edit_mode": False, "nav_active": "cartera"})


def pago_update(request, pk):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:pagos")

    obj = get_object_or_404(Pago, pk=pk, cuenta__concepto__school=school)  # ✅

    if request.method == "POST":
        form = PagoForm(request.POST, instance=obj, school=school)
        if form.is_valid():
            with transaction.atomic():
                original = Pago.objects.select_related("cuenta").get(pk=obj.pk)
                pago = form.save(commit=False)
                cuenta = pago.cuenta

                delta = (pago.valor_pagado or Decimal("0")) - (original.valor_pagado or Decimal("0"))
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
        form = PagoForm(instance=obj, school=school)

    return render(request, "cartera/pago_form.html", {"form": form, "edit_mode": True, "obj": obj, "nav_active": "cartera"})


def pago_delete(request, pk):
    school = getattr(request, "school", None)
    if not school:
        messages.error(request, "No se detectó el colegio del dominio.")
        return redirect("cartera:pagos")

    obj = get_object_or_404(Pago, pk=pk, cuenta__concepto__school=school)  # ✅

    if request.method == "POST":
        with transaction.atomic():
            cuenta = obj.cuenta
            cuenta.saldo_pendiente = (cuenta.saldo_pendiente or Decimal("0")) + (obj.valor_pagado or Decimal("0"))
            if cuenta.saldo_pendiente > 0:
                cuenta.pagada = False
            cuenta.save(update_fields=["saldo_pendiente", "pagada"])
            obj.delete()

        messages.success(request, "Pago eliminado.")
        return redirect("cartera:pagos")

    return render(request, "cartera/pago_confirm_delete.html", {"obj": obj, "nav_active": "cartera"})