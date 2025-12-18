from django import forms
from django.core.exceptions import ValidationError
from .models import Estudiante, Docente, Curso, AsignaturaOferta, AnioLectivo, AsignaturaCatalogo, Periodo, Logro
from decimal import Decimal
from django.contrib.auth.models import User, Group
from cuentas.models import PerfilUsuario
from django.utils import timezone

def password_por_colegio_y_anio(school):
    anio = timezone.now().year

    if not school:
        return f"Clave{anio}"

    base = (getattr(school, "slug", None) or school.name or "Colegio").strip()
    base = "".join(ch for ch in base if ch.isalnum())

    return f"{base}{anio}"

class EstudianteForm(forms.ModelForm):
    fecha_nacimiento = forms.DateField(
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-input"},
            format="%Y-%m-%d"
        ),
        input_formats=["%Y-%m-%d"],
        required=True
    )

    class Meta:
        model = Estudiante
        fields = [
            "nombres", "apellidos", "identificacion", "fecha_nacimiento",
            "direccion", "telefono", "correo", "curso", "acudiente",
            "foto"
        ]

    def clean_identificacion(self):
        identificacion = (self.cleaned_data.get("identificacion") or "").strip()
        qs = Estudiante.objects.filter(identificacion=identificacion)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un estudiante con esa identificación.")
        return identificacion

    def save(self, commit=True):
        estudiante = super().save(commit=False)
        if commit:
            estudiante.save()
        return estudiante

class DocenteForm(forms.ModelForm):
    class Meta:
        model = Docente
        fields = [
            "nombres", "apellidos", "identificacion",
            "correo", "telefono", "curso_asignado", "foto"
        ]

    def clean_identificacion(self):
        identificacion = (self.cleaned_data.get("identificacion") or "").strip()
        qs = Docente.objects.filter(identificacion=identificacion)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un docente con esa identificación.")
        return identificacion

    def save(self, commit=True):
        docente = super().save(commit=False)
        if commit:
            docente.save()
        return docente

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ["nombre", "grado", "jornada"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input"}),
            "grado": forms.TextInput(attrs={"class": "form-input"}),
            "jornada": forms.TextInput(attrs={"class": "form-input"}),
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        grado = (self.cleaned_data.get("grado") or "").strip()
        qs = Curso.objects.filter(nombre=nombre, grado=grado)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un curso con ese nombre y grado.")
        return nombre

class AsignaturaCatalogoForm(forms.ModelForm):
    class Meta:
        model = AsignaturaCatalogo
        fields = ["nombre", "area"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input", "placeholder": "Matemáticas"}),
            "area": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ciencias, Lenguaje... (opcional)"}),
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        qs = AsignaturaCatalogo.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe una asignatura con ese nombre.")
        return nombre

class AsignaturaOfertaForm(forms.ModelForm):
    class Meta:
        model = AsignaturaOferta
        fields = ["anio", "curso", "asignatura", "docente", "intensidad_horaria"]
        widgets = {
            "anio": forms.Select(attrs={"class": "form-select"}),
            "curso": forms.Select(attrs={"class": "form-select"}),
            "asignatura": forms.Select(attrs={"class": "form-select"}),
            "docente": forms.Select(attrs={"class": "form-select"}),
            "intensidad_horaria": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }

    def clean(self):
        cleaned = super().clean()
        anio = cleaned.get("anio")
        curso = cleaned.get("curso")
        asignatura = cleaned.get("asignatura")
        if anio and curso and asignatura:
            qs = AsignaturaOferta.objects.filter(anio=anio, curso=curso, asignatura=asignatura)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe esta oferta (Año+Curso+Asignatura).")
        return cleaned


class OfertaBulkForm(forms.Form):
    """
    Crea varias AsignaturaOferta en un paso:
    - mismo año lectivo
    - misma asignatura del catálogo
    - varios cursos
    - (opcional) mismo docente e intensidad
    """
    anio = forms.ModelChoiceField(
        queryset=AnioLectivo.objects.all().order_by("-activo", "-nombre"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    asignatura = forms.ModelChoiceField(
        queryset=AsignaturaCatalogo.objects.all().order_by("nombre"),
        widget=forms.Select(attrs={"class": "form-select"})
    )
    cursos = forms.ModelMultipleChoiceField(
        queryset=Curso.objects.all().order_by("grado", "nombre"),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 10})
    )
    docente = forms.ModelChoiceField(
        queryset=Docente.objects.all().order_by("apellidos", "nombres"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    intensidad_horaria = forms.IntegerField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "Horas/semana (opcional)"})
    )

    def clean(self):
        cleaned = super().clean()
        # Nada especial aquí; validamos duplicados en la vista antes de crear
        return cleaned

# ---------- PERIODOS ----------
class PeriodoForm(forms.ModelForm):
    class Meta:
        model = Periodo
        fields = ["anio", "numero", "nombre", "peso"]
        widgets = {
            "anio": forms.Select(attrs={"class": "form-select"}),
            "numero": forms.NumberInput(attrs={"class": "form-input", "min": 1, "max": 4}),
            "nombre": forms.TextInput(attrs={"class": "form-input", "placeholder": "Periodo 1"}),
            "peso": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
        }

    def clean_peso(self):
        peso = self.cleaned_data.get("peso")
        if peso is None or peso <= 0:
            raise ValidationError("El peso debe ser mayor que 0.")
        return peso

    def clean(self):
        # unique_together (anio, numero) ya lo asegura la BD, pero validamos amistosamente
        cleaned = super().clean()
        anio = cleaned.get("anio")
        numero = cleaned.get("numero")
        if anio and numero:
            qs = Periodo.objects.filter(anio=anio, numero=numero)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un periodo con ese número para el año seleccionado.")
        return cleaned


# ---------- LOGROS ----------
class LogroForm(forms.ModelForm):
    class Meta:
        model = Logro
        fields = ["oferta", "periodo", "tipo", "titulo", "descripcion", "peso"]
        widgets = {
            "oferta": forms.Select(attrs={"class": "form-select"}),
            "periodo": forms.Select(attrs={"class": "form-select"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),   # 👈 nuevo
            "titulo": forms.TextInput(attrs={"class": "form-input"}),
            "descripcion": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "peso": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
        }

    def clean_peso(self):
        peso = self.cleaned_data.get("peso")
        if peso is None or peso < 0 or peso > Decimal("100.00"):
            raise ValidationError("El peso debe estar entre 0 y 100.")
        return peso

    def clean(self):
        cleaned = super().clean()
        oferta = cleaned.get("oferta")
        periodo = cleaned.get("periodo")
        titulo = (cleaned.get("titulo") or "").strip()
        if oferta and periodo:
            if oferta.anio_id != periodo.anio_id:
                raise ValidationError("El periodo debe pertenecer al mismo año lectivo de la oferta.")

            # Evitar duplicar título dentro de la misma (oferta, periodo)
            qs = Logro.objects.filter(oferta=oferta, periodo=periodo, titulo__iexact=titulo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un logro con ese título para esta oferta y periodo.")
        return cleaned

class AnioLectivoForm(forms.ModelForm):
    class Meta:
        model = AnioLectivo
        fields = ["nombre", "fecha_inicio", "fecha_fin", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: 2026"
            }),
            "fecha_inicio": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "fecha_fin": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "activo": forms.CheckboxInput(),
        }