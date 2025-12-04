from django.shortcuts import render


def home(request):
    """
    Vista principal para mostrar el template base.html
    """
    return render(request, 'colegioapp/base.html')


