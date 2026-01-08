from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ContactoForm
from .models import PublicPage, HomeBlock, NewsPost, SchoolPublicConfig, HomeHeroSlide, AboutSlide


def _get_school(request):
    return getattr(request, "school", None) or getattr(request, "colegio_actual", None)

def _get_page(school, slug):
    if not school:
        return None
    return PublicPage.objects.filter(school=school, slug=slug, is_active=True).first()

def home(request):
    school = _get_school(request)
    page = _get_page(school, "home")
    blocks = HomeBlock.objects.filter(school=school, is_active=True).order_by("order") if school else []
    config = SchoolPublicConfig.objects.filter(school=school).first() if school else None

    slides = HomeHeroSlide.objects.filter(school=school, is_active=True) if school else []

    return render(request, "sitio/home_publico.html", {
        "page": page,
        "blocks": blocks,
        "config": config,
        "slides": slides,
    })

def nosotros(request):
    school = _get_school(request)

    # OJO: en tu admin veo que tienes el slug "nostros" (sin la segunda "o")
    # Si ya lo cambiaste a "nosotros" en admin, deja "nosotros". Si no, usa "nostros".
    page = _get_page(school, "nostros")  # o "nosotros"

    mision = _get_page(school, "mision")
    vision = _get_page(school, "vision")
    historia = _get_page(school, "historia")

    slides = AboutSlide.objects.filter(school=school, is_active=True).order_by("order") if school else []

    return render(request, "sitio/nosotros.html", {
        "page": page,
        "slides": slides,
        "mision": mision,
        "vision": vision,
        "historia": historia,
    })

def admisiones(request):
    school = _get_school(request)
    page = _get_page(school, "admisiones")
    config = SchoolPublicConfig.objects.filter(school=school).first() if school else None
    return render(request, "sitio/admisiones.html", {"page": page, "config": config})

def noticias(request):
    school = _get_school(request)
    posts = NewsPost.objects.filter(school=school, is_published=True) if school else []
    config = SchoolPublicConfig.objects.filter(school=school).first() if school else None
    return render(request, "sitio/noticias.html", {"posts": posts})

def contacto(request):
    school = _get_school(request)
    page = _get_page(school, "contacto")
    config = SchoolPublicConfig.objects.filter(school=school).first() if school else None

    if request.method == "POST":
        form = ContactoForm(request.POST)
        if form.is_valid():
            # ✅ aquí luego conectas el envío de correo (si ya lo tienes)
            messages.success(request, "✅ Mensaje enviado correctamente.")
            return redirect("sitio:contacto")
        else:
            messages.error(request, "❌ Revisa los campos del formulario.")
    else:
        form = ContactoForm()

    return render(request, "sitio/contacto.html", {
        "page": page,
        "config": config,
        "form": form,   # ✅ ESTO era lo que faltaba
    })
