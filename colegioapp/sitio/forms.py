from django import forms

class ContactoForm(forms.Form):
    nombre = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        "placeholder": "Tu nombre",
        "class": "input",
        "style": "width:100%;padding:10px;border:1px solid #cfd8dc;border-radius:8px;"
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        "placeholder": "tu@correo.com",
        "class": "input",
        "style": "width:100%;padding:10px;border:1px solid #cfd8dc;border-radius:8px;"
    }))
    telefono = forms.CharField(required=False, max_length=30, widget=forms.TextInput(attrs={
        "placeholder": "Opcional",
        "style": "width:100%;padding:10px;border:1px solid #cfd8dc;border-radius:8px;"
    }))
    asunto = forms.CharField(max_length=120, widget=forms.TextInput(attrs={
        "placeholder": "Asunto",
        "style": "width:100%;padding:10px;border:1px solid #cfd8dc;border-radius:8px;"
    }))
    mensaje = forms.CharField(widget=forms.Textarea(attrs={
        "rows": 5,
        "placeholder": "Cuéntanos en qué podemos ayudarte",
        "style": "width:100%;padding:10px;border:1px solid #cfd8dc;border-radius:8px;"
    }))
    autorizacion = forms.BooleanField(label="Autorización de datos", required=True)