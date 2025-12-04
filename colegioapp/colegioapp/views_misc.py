from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

@login_required
def post_login_redirect(request):
    u = request.user
    if u.groups.filter(name="Estudiante").exists():
        # asegúrate de que esta ruta exista (ver 4)
        return redirect(reverse("academico:portal"))

    if u.is_staff or u.is_superuser:
        return redirect(reverse("home"))

    return redirect(reverse("home"))