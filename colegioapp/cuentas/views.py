from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UsuarioCreateForm, UsuarioUpdateForm
from django.db.models import Q
from academico.models import Estudiante, Docente

def es_superusuario(user):
    return user.is_superuser  # o usar permisos específicos

@login_required
@user_passes_test(es_superusuario)
def usuario_list(request):
    grupo_id = request.GET.get('grupo')
    usuarios = User.objects.all().order_by('username')

    grupos = Group.objects.all()
    if grupo_id:
        usuarios = usuarios.filter(groups__id=grupo_id)

    context = {
        'usuarios': usuarios,
        'grupos': grupos,
        'grupo_id': grupo_id,
        'nav_active': 'cuentas',
    }
    return render(request, 'cuentas/usuario_list.html', context)


@login_required
@user_passes_test(es_superusuario)
def usuario_create(request):
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('cuentas:usuarios_list')
    else:
        form = UsuarioCreateForm()

    return render(request, 'cuentas/usuario_form.html', {
        'form': form,
        'nav_active': 'cuentas',
        'editando': False,
    })


@login_required
@user_passes_test(es_superusuario)
def usuario_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UsuarioUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('cuentas:usuarios_list')
    else:
        form = UsuarioUpdateForm(instance=user)

    return render(request, 'cuentas/usuario_form.html', {
        'form': form,
        'nav_active': 'cuentas',
        'editando': True,
    })

def es_superusuario(user):
    return user.is_superuser  # o usar permisos específicos


def puede_buscar(user):
    """
    Puede usar el buscador global:
    - superusuario
    - staff (admin)
    - grupo Rector
    """
    return (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name="Rector").exists()
    )


@login_required
@user_passes_test(es_superusuario)
def usuario_list(request):
    grupo_id = request.GET.get('grupo')
    usuarios = User.objects.all().order_by('username')

    grupos = Group.objects.all()
    if grupo_id:
        usuarios = usuarios.filter(groups__id=grupo_id)

    context = {
        'usuarios': usuarios,
        'grupos': grupos,
        'grupo_id': grupo_id,
        'nav_active': 'cuentas',
    }
    return render(request, 'cuentas/usuario_list.html', context)


@login_required
@user_passes_test(es_superusuario)
def usuario_create(request):
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('cuentas:usuarios_list')
    else:
        form = UsuarioCreateForm()

    return render(request, 'cuentas/usuario_form.html', {
        'form': form,
        'nav_active': 'cuentas',
        'editando': False,
    })


@login_required
@user_passes_test(es_superusuario)
def usuario_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UsuarioUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('cuentas:usuarios_list')
    else:
        form = UsuarioUpdateForm(instance=user)

    return render(request, 'cuentas/usuario_form.html', {
        'form': form,
        'nav_active': 'cuentas',
        'editando': True,
    })


# 🔍 NUEVA VISTA: buscador global de personas
@login_required
@user_passes_test(puede_buscar)
def buscar_persona(request):
    q = request.GET.get("q", "").strip()
    estudiantes = []
    docentes = []
    usuarios = []

    if q:
        # Estudiantes: nombre, apellidos, identificación
        estudiantes = (
            Estudiante.objects
            .select_related("curso")
            .filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(identificacion__icontains=q)
            )
        )

        # Docentes
        docentes = (
            Docente.objects
            .select_related("curso_asignado")
            .filter(
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(identificacion__icontains=q)
            )
        )

        # Usuarios
        usuarios = (
            User.objects
            .filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q)
            )
            .distinct()
        )

    ctx = {
        "q": q,
        "estudiantes": estudiantes,
        "docentes": docentes,
        "usuarios": usuarios,
        "nav_active": "cuentas",
    }
    return render(request, "cuentas/buscar_persona.html", ctx)