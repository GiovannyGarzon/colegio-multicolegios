from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from .forms import UsuarioCreateForm, UsuarioUpdateForm
from academico.models import Estudiante, Docente


# --- PERMISOS --------------------------------------------------------

def es_admin_usuarios(user):
    """
    Puede administrar usuarios:
    - superusuario
    - staff
    - o del grupo Rector
    """
    return (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name="Rector").exists()
    )


def puede_buscar(user):
    """
    Puede usar el buscador global (misma lógica que admin usuarios).
    """
    return es_admin_usuarios(user)


# --- USUARIOS --------------------------------------------------------

@login_required
@user_passes_test(es_admin_usuarios)
def usuario_list(request):
    grupo_id = request.GET.get('grupo')
    colegio = getattr(request, "colegio_actual", None)

    # Solo usuarios del colegio actual
    usuarios = User.objects.all().order_by('username')
    if colegio is not None:
        usuarios = usuarios.filter(perfil__school=colegio)

    # Filtro por grupo
    if grupo_id:
        usuarios = usuarios.filter(groups__id=grupo_id)

    grupos = Group.objects.all()

    context = {
        'usuarios': usuarios,
        'grupos': grupos,
        'grupo_id': grupo_id,
        'nav_active': 'cuentas',
    }
    return render(request, 'cuentas/usuario_list.html', context)


@login_required
@user_passes_test(es_admin_usuarios)
def usuario_create(request):
    colegio = getattr(request, "colegio_actual", None)

    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()

            # Asegurar que el perfil queda amarrado al colegio actual
            perfil = getattr(user, "perfil", None)
            if perfil and colegio and perfil.school is None:
                perfil.school = colegio
                perfil.save()

            return redirect('cuentas:usuarios_list')
    else:
        form = UsuarioCreateForm()

    return render(request, 'cuentas/usuario_form.html', {
        'form': form,
        'nav_active': 'cuentas',
        'editando': False,
    })


@login_required
@user_passes_test(es_admin_usuarios)
def usuario_update(request, pk):
    colegio = getattr(request, "colegio_actual", None)
    user = get_object_or_404(User, pk=pk)

    # Seguridad extra: no permitir editar usuarios de otro colegio
    perfil = getattr(user, "perfil", None)
    if colegio and perfil and perfil.school_id != colegio.id and not request.user.is_superuser:
        # podrías mostrar un mensaje de error si quieres
        return redirect('cuentas:usuarios_list')

    if request.method == 'POST':
        form = UsuarioUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save()

            perfil = getattr(user, "perfil", None)
            if perfil and colegio and perfil.school is None:
                perfil.school = colegio
                perfil.save()

            return redirect('cuentas:usuarios_list')
    else:
        form = UsuarioUpdateForm(instance=user)

    return render(request, 'cuentas/usuario_form.html', {
        'form': form,
        'nav_active': 'cuentas',
        'editando': True,
    })


# --- BUSCADOR GLOBAL -------------------------------------------------

@login_required
@user_passes_test(puede_buscar)
def buscar_persona(request):
    colegio = getattr(request, "colegio_actual", None)
    q = request.GET.get("q", "").strip()

    estudiantes = []
    docentes = []
    usuarios = []

    if q:
        # Estudiantes (asumiendo que Estudiante tiene campo school o similar,
        # ajústalo a tu modelo real: e.g. curso__colegio=colegio)
        est_qs = Estudiante.objects.select_related("curso")
        if colegio:
            est_qs = est_qs.filter(curso__colegio=colegio)
        estudiantes = est_qs.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(identificacion__icontains=q)
        )

        # Docentes (ajusta filtro al campo correcto de colegio)
        doc_qs = Docente.objects.all()
        if colegio:
            doc_qs = doc_qs.filter(colegio=colegio)
        docentes = doc_qs.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(identificacion__icontains=q)
        )

        # Usuarios solo del colegio actual
        usr_qs = User.objects.all()
        if colegio:
            usr_qs = usr_qs.filter(perfil__school=colegio)
        usuarios = usr_qs.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        ).distinct()

    ctx = {
        "q": q,
        "estudiantes": estudiantes,
        "docentes": docentes,
        "usuarios": usuarios,
        "nav_active": "cuentas",
    }
    return render(request, "cuentas/buscar_persona.html", ctx)