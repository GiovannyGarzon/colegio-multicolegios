from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

from myapp.models import School


class SchoolMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]  # ej: giongabi.local o sannicolas.local

        # Buscar el colegio por dominio
        colegio = School.objects.filter(domain=host).first()

        # IMPORTANTE: exponer con ambos nombres
        request.school = colegio          # lo que usan los templates
        request.colegio_actual = colegio  # lo que usa SchoolAccessMiddleware (si quieres mantenerlo)

        return self.get_response(request)


class SchoolAccessMiddleware:
    """
    Bloquea el acceso si el usuario intenta entrar a un colegio distinto
    al que tiene asignado en su perfil.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        colegio = getattr(request, "colegio_actual", None)

        if not user.is_authenticated:
            return None

        # Superusuarios: libres
        if user.is_superuser:
            return None

        # No validar en /admin/
        if request.path.startswith("/admin/"):
            return None

        perfil = getattr(user, "perfil", None)

        # Sin perfil o sin colegio asignado -> bloquear
        if not perfil or not perfil.school:
            messages.error(
                request,
                "Tu usuario no tiene un colegio asignado. Comunícate con coordinación."
            )
            logout(request)
            return redirect("login")

        # Candado por colegio
        if colegio and perfil.school_id != colegio.id:
            messages.error(
                request,
                "Este usuario pertenece a otro colegio. Debes ingresar al portal de tu plantel."
            )
            logout(request)
            return redirect("login")

        return None