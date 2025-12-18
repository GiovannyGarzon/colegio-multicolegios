from django import forms
from datetime import date

from .models import Cargo, Empleado, Proveedor, Contrato
from academico.models import Matricula, Estudiante, Curso, AnioLectivo


class SchoolScopedModelForm(forms.ModelForm):
    """
    Base: recibe `school` y lo guarda.
    Todos los forms deben instanciarse como: Form(..., school=request.school)
    """
    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)


# -------------------------
# CARGO
# -------------------------
class CargoForm(SchoolScopedModelForm):
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
        # ✅ si Cargo tiene school:
        if self.school is not None and hasattr(Cargo, "school_id"):
            qs = qs.filter(school=self.school)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ya existe un cargo con ese nombre.")
        return nombre

    def save(self, commit=True):
        obj = super().save(commit=False)
        # ✅ si Cargo tiene school
        if self.school is not None and hasattr(obj, "school_id"):
            obj.school = self.school
        if commit:
            obj.save()
        return obj


# -------------------------
# EMPLEADO
# -------------------------
class EmpleadoForm(SchoolScopedModelForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ filtra el combo de cargo por school
        if "cargo" in self.fields and self.school is not None:
            qs = Cargo.objects.all()
            if hasattr(Cargo, "school_id"):
                qs = qs.filter(school=self.school)
            self.fields["cargo"].queryset = qs.order_by("nombre")

    def clean_identificacion(self):
        identificacion = (self.cleaned_data.get("identificacion") or "").strip()

        qs = Empleado.objects.filter(identificacion=identificacion)
        # ✅ si Empleado tiene school:
        if self.school is not None and hasattr(Empleado, "school_id"):
            qs = qs.filter(school=self.school)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ya existe un empleado con esa identificación.")
        return identificacion

    def clean(self):
        cleaned = super().clean()

        # ✅ seguridad: el cargo debe pertenecer al mismo school
        cargo = cleaned.get("cargo")
        if cargo and self.school is not None and hasattr(cargo, "school_id"):
            if cargo.school_id != getattr(self.school, "id", None):
                self.add_error("cargo", "El cargo no pertenece a este colegio.")

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        # ✅ si Empleado tiene school
        if self.school is not None and hasattr(obj, "school_id"):
            obj.school = self.school
        if commit:
            obj.save()
        return obj


# -------------------------
# PROVEEDOR
# -------------------------
class ProveedorForm(SchoolScopedModelForm):
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
        # ✅ si Proveedor tiene school:
        if self.school is not None and hasattr(Proveedor, "school_id"):
            qs = qs.filter(school=self.school)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ya existe un proveedor con ese NIT.")
        return nit

    def save(self, commit=True):
        obj = super().save(commit=False)
        # ✅ si Proveedor tiene school
        if self.school is not None and hasattr(obj, "school_id"):
            obj.school = self.school
        if commit:
            obj.save()
        return obj


# -------------------------
# CONTRATO
# -------------------------
class ContratoForm(SchoolScopedModelForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ filtra el combo de empleado por school
        if "empleado" in self.fields and self.school is not None:
            qs = Empleado.objects.all()
            if hasattr(Empleado, "school_id"):
                qs = qs.filter(school=self.school)
            self.fields["empleado"].queryset = qs.order_by("apellidos", "nombres")

    def clean(self):
        cleaned = super().clean()
        fi = cleaned.get("fecha_inicio")
        ff = cleaned.get("fecha_fin")
        valor = cleaned.get("valor")
        empleado = cleaned.get("empleado")

        if fi and ff and ff < fi:
            self.add_error("fecha_fin", "La fecha de fin no puede ser anterior a la fecha de inicio.")

        if valor is not None and valor < 0:
            self.add_error("valor", "El valor debe ser mayor o igual a 0.")

        # ✅ seguridad: empleado del mismo colegio
        if empleado and self.school is not None and hasattr(empleado, "school_id"):
            if empleado.school_id != getattr(self.school, "id", None):
                self.add_error("empleado", "El empleado no pertenece a este colegio.")

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        # ✅ si Contrato tiene school
        if self.school is not None and hasattr(obj, "school_id"):
            obj.school = self.school
        if commit:
            obj.save()
        return obj


# -------------------------
# MATRÍCULA
# -------------------------
class MatriculaForm(SchoolScopedModelForm):
    class Meta:
        model = Matricula
        fields = ["estudiante", "anio", "curso", "activo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.school is not None:
            # ✅ estudiantes del colegio
            self.fields["estudiante"].queryset = (
                Estudiante.objects.filter(school=self.school).order_by("apellidos", "nombres")
            )

            # Si Curso tiene school:
            if hasattr(Curso, "school_id"):
                self.fields["curso"].queryset = Curso.objects.filter(school=self.school).order_by("grado", "nombre")
            else:
                self.fields["curso"].queryset = Curso.objects.all().order_by("grado", "nombre")

            # Si AnioLectivo tiene school:
            if hasattr(AnioLectivo, "school_id"):
                self.fields["anio"].queryset = AnioLectivo.objects.filter(school=self.school).order_by("nombre")
            else:
                self.fields["anio"].queryset = AnioLectivo.objects.all().order_by("nombre")

    def clean(self):
        cleaned = super().clean()
        est = cleaned.get("estudiante")
        curso = cleaned.get("curso")
        anio = cleaned.get("anio")

        # ✅ seguridad: estudiante debe ser del colegio
        if est and self.school is not None and hasattr(est, "school_id"):
            if est.school_id != getattr(self.school, "id", None):
                self.add_error("estudiante", "El estudiante no pertenece a este colegio.")

        # ✅ seguridad: curso/año si tienen school
        if curso and self.school is not None and hasattr(curso, "school_id"):
            if curso.school_id != getattr(self.school, "id", None):
                self.add_error("curso", "El curso no pertenece a este colegio.")

        if anio and self.school is not None and hasattr(anio, "school_id"):
            if anio.school_id != getattr(self.school, "id", None):
                self.add_error("anio", "El año lectivo no pertenece a este colegio.")

        return cleaned