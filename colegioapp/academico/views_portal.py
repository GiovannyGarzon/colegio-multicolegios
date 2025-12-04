from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseForbidden
from .models import Estudiante, AnioLectivo

def _get_estudiante(request):
    try:
        return request.user.estudiante
    except Estudiante.DoesNotExist:
        return None

@login_required
def portal_inicio(request):
    est = _get_estudiante(request)
    if not est:
        return HttpResponseForbidden("Tu usuario no está vinculado a un estudiante.")
    anio = AnioLectivo.objects.filter(activo=True).first()
    return render(request, "portal/inicio.html", {"est": est, "anio": anio})