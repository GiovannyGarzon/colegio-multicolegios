from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    return render(request, "colegioapp/base.html", {"nav_active": "inicio"})