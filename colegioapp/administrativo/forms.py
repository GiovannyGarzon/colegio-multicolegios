from django import forms
from .models import Cargo, Empleado, Proveedor, Contrato
from academico.models import Matricula, Estudiante, Curso, AnioLectivo
from datetime import date

class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = ["nombre", "descripcion", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ej. Coordinador académico"}),
            "descripcion": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check"}),
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        qs = Cargo.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un cargo con ese nombre.")
        return nombre

class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            "nombres", "apellidos", "identificacion", "cargo",
            "telefono", "correo", "direccion", "fecha_ingreso",
            "salario", "activo",
        ]
        widgets = {
            "nombres": forms.TextInput(attrs={"class": "form-input"}),
            "apellidos": forms.TextInput(attrs={"class": "form-input"}),
            "identificacion": forms.TextInput(attrs={"class": "form-input"}),
            "cargo": forms.Select(attrs={"class": "form-select"}),
            "telefono": forms.TextInput(attrs={"class": "form-input"}),
            "correo": forms.EmailInput(attrs={"class": "form-input"}),
            "direccion": forms.TextInput(attrs={"class": "form-input"}),
            "fecha_ingreso": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "salario": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check"}),
        }

    def clean_identificacion(self):
        identificacion = (self.cleaned_data.get("identificacion") or "").strip()
        qs = Empleado.objects.filter(identificacion=identificacion)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un empleado con esa identificación.")
        return identificacion

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "nit", "direccion", "telefono", "correo", "descripcion"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-input"}),
            "nit": forms.TextInput(attrs={"class": "form-input"}),
            "direccion": forms.TextInput(attrs={"class": "form-input"}),
            "telefono": forms.TextInput(attrs={"class": "form-input"}),
            "correo": forms.EmailInput(attrs={"class": "form-input"}),
            "descripcion": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def clean_nit(self):
        nit = (self.cleaned_data.get("nit") or "").strip()
        qs = Proveedor.objects.filter(nit=nit)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un proveedor con ese NIT.")
        return nit

class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["empleado", "tipo_contrato", "fecha_inicio", "fecha_fin", "valor", "observaciones"]
        widgets = {
            "empleado": forms.Select(attrs={"class": "form-select"}),
            "tipo_contrato": forms.TextInput(attrs={"class": "form-input"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "valor": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "observaciones": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        fi = cleaned.get("fecha_inicio")
        ff = cleaned.get("fecha_fin")
        valor = cleaned.get("valor")

        if fi and ff and ff < fi:
            self.add_error("fecha_fin", "La fecha de fin no puede ser anterior a la fecha de inicio.")

        if valor is not None and valor < 0:
            self.add_error("valor", "El valor debe ser mayor o igual a 0.")

        return cleaned

class MatriculaForm(forms.ModelForm):
    class Meta:
        model = Matricula
        fields = ["estudiante", "anio", "curso", "activo"]

        widgets = {
            "fecha_matricula": forms.DateInput(attrs={"type": "date"}),
        }