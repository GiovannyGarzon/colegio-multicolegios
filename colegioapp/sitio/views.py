from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from datetime import date

from .forms import ContactoForm


def home(request):
    return render(request, "sitio/home_publico.html")

def nosotros(request):
    return render(request, "sitio/nosotros.html")

def admisiones(request):
    return render(request, "sitio/admisiones.html")

def noticias(request):
    return render(request, "sitio/noticias.html", {"today": date.today()})

def contacto(request):
    if request.method == "POST":
        form = ContactoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Opción A: enviar email (configura EMAIL_* en settings.py)
            try:
                send_mail(
                    subject=f"[Contacto CEI GIN GABY] {data['asunto']}",
                    message=(
                        f"Nombre: {data['nombre']}\n"
                        f"Email: {data['email']}\n"
                        f"Teléfono: {data.get('telefono') or '-'}\n\n"
                        f"Mensaje:\n{data['mensaje']}"
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", data["email"]),
                    recipient_list=[getattr(settings, "CONTACT_EMAIL", "gingabisas@gmail.com")],
                    fail_silently=True,
                )
            except BadHeaderError:
                messages.error(request, "Ha ocurrido un error al enviar tu mensaje.")
            else:
                messages.success(request, "¡Tu mensaje fue enviado! Te responderemos pronto.")
                return redirect("sitio:contacto")
        else:
            messages.error(request, "Por favor corrige los campos marcados.")
    else:
        form = ContactoForm()
    return render(request, "sitio/contacto.html", {"form": form})