from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Avg
from .models import Noticia
from .forms import NoticiaForm
from academico.models import Estudiante, Observador
from datetime import date

from academico.models import Periodo, AnioLectivo, AsignaturaOferta, CalificacionLogro


def es_staff(u):
    return u.is_staff or u.is_superuser


def _edad(desde):
    if not desde:
        return None
    hoy = date.today()
    return hoy.year - desde.year - ((hoy.month, hoy.day) < (desde.month, desde.day))


@login_required
def tablero_home(request):
    # =======================
    # 1) Noticias por colegio
    # =======================
    qs = Noticia.objects.filter(activo=True)

    school = getattr(request, "school", None)
    if school is not None:
        qs = qs.filter(school=school)

    qs = qs.order_by("-fecha_publicacion")

    # máximo 5
    noticias_qs = qs[:5]
    noticia_destacada = noticias_qs[0] if noticias_qs else None
    noticias_restantes = noticias_qs[1:] if len(noticias_qs) > 1 else []

    # =======================
    # 2) Perfil base
    # =======================
    perfil = {
        "nombre": request.user.get_full_name() or request.user.username,
        "usuario": request.user.username,
        "email": request.user.email,
        "roles": [g.name for g in request.user.groups.all()],
        "es_staff": request.user.is_staff or request.user.is_superuser,
    }

    estudiante = Estudiante.objects.select_related("curso").filter(user=request.user).first()
    seguimientos = []
    promedios_tablero = []
    anio_activo = None
    periodo_actual = None

    if estudiante:
        perfil["tipo"] = "estudiante"
        perfil["curso"] = str(estudiante.curso) if estudiante.curso else "Sin curso asignado"
        perfil["identificacion"] = estudiante.identificacion
        perfil["edad"] = _edad(getattr(estudiante, "fecha_nacimiento", None))

        # Año lectivo activo
        anio_activo = AnioLectivo.objects.filter(activo=True).first()
        if anio_activo and estudiante.curso:
            # Ofertas de ese estudiante en ese año
            ofertas = AsignaturaOferta.objects.select_related("asignatura").filter(
                anio=anio_activo,
                curso=estudiante.curso,
            )
            for of in ofertas:
                qs_notas = CalificacionLogro.objects.filter(
                    estudiante=estudiante,
                    logro__oferta=of
                )
                if qs_notas.exists():
                    prom = qs_notas.aggregate(p=Avg("nota"))["p"]
                    promedios_tablero.append(
                        {"asignatura": of.asignatura.nombre, "promedio": prom}
                    )

            # Último período del año activo
            periodo_actual = (
                Periodo.objects.filter(anio=anio_activo).order_by("-numero").first()
            )

        # Seguimientos (observador)
        seguimientos = (
            Observador.objects.filter(estudiante=estudiante)
            .order_by("-fecha")[:5]
        )

    ctx = {
        "noticia_destacada": noticia_destacada,
        "noticias": noticias_restantes,
        "perfil": perfil,
        "estudiante": estudiante,
        "seguimientos": seguimientos,
        "nav_active": "tablero",
        "promedios_tablero": promedios_tablero,
        "anio_activo": anio_activo,
        "periodo_actual": periodo_actual,
    }
    return render(request, "tablero/tablero_home.html", ctx)


@login_required
def archivo(request):
    # ver todas (activas e inactivas) PERO del colegio actual
    qs = Noticia.objects.all()
    school = getattr(request, "school", None)
    if school is not None:
        qs = qs.filter(school=school)
    qs = qs.order_by("-fecha_publicacion")
    return render(request, "tablero/archivo.html", {"noticias": qs})


@login_required
@user_passes_test(es_staff)
def crear(request):
    if request.method == "POST":
        form = NoticiaForm(request.POST, request.FILES)
        if form.is_valid():
            n = form.save(commit=False)
            n.publicado_por = request.user
            # 🔴 MUY IMPORTANTE: asignar colegio
            n.school = getattr(request, "school", None)
            n.save()
            messages.success(request, "Noticia publicada.")
            return redirect("tablero:home")
    else:
        form = NoticiaForm()
    return render(request, "tablero/form.html", {"form": form, "title": "Nueva noticia"})


@login_required
@user_passes_test(es_staff)
def editar(request, pk):
    school = getattr(request, "school", None)
    n = get_object_or_404(Noticia, pk=pk, school=school)
    if request.method == "POST":
        form = NoticiaForm(request.POST, request.FILES, instance=n)
        if form.is_valid():
            form.save()
            messages.success(request, "Noticia actualizada.")
            return redirect("tablero:home")
    else:
        form = NoticiaForm(instance=n)
    return render(request, "tablero/form.html", {"form": form, "title": f"Editar: {n.titulo}"})


@login_required
@user_passes_test(es_staff)
def eliminar(request, pk):
    school = getattr(request, "school", None)
    n = get_object_or_404(Noticia, pk=pk, school=school)
    if request.method == "POST":
        n.delete()
        messages.success(request, "Noticia eliminada.")
        return redirect("tablero:home")
    return render(request, "tablero/confirm_delete.html", {"obj": n})