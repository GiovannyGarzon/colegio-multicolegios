from django import forms
from django.core.exceptions import ValidationError
from .models import Estudiante, Docente, Curso, AsignaturaOferta, AnioLectivo, AsignaturaCatalogo, Periodo, Logro
from decimal import Decimal
from django.contrib.auth.models import User, Group
from cuentas.models import PerfilUsuario


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
        widgets = {
            "nombres": forms.TextInput(attrs={"class": "form-input"}),
            "apellidos": forms.TextInput(attrs={"class": "form-input"}),
            "identificacion": forms.TextInput(attrs={"class": "form-input"}),
            "direccion": forms.TextInput(attrs={"class": "form-input"}),
            "telefono": forms.TextInput(attrs={"class": "form-input"}),
            "correo": forms.EmailInput(attrs={"class": "form-input"}),
            "curso": forms.Select(attrs={"class": "form-select"}),
            "acudiente": forms.TextInput(attrs={"class": "form-input"}),
            "foto": forms.FileInput(attrs={
                "class": "form-input",
                "accept": "image/*"
            }),
        }

    def clean_identificacion(self):
        identificacion = (self.cleaned_data.get("identificacion") or "").strip()
        qs = Estudiante.objects.filter(identificacion=identificacion)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un estudiante con esa identificación.")
        return identificacion

    def save(self, commit=True):
        """
        - Guarda el Estudiante
        - Si no tiene user asociado, crea:
            - User con:
                username = identificación
                password = GinGaby2025
            - Lo mete al grupo 'Estudiante'
            - Crea Perfil copiando fecha_nacimiento, telefono, direccion y foto
        """
        estudiante = super().save(commit=False)

        creando = estudiante.pk is None  # True si es nuevo

        if commit:
            estudiante.save()

        # Solo crear usuario/perfil cuando el estudiante es nuevo
        if creando and estudiante.user is None:
            ident = estudiante.identificacion.strip()

            # Opcional: asegurarnos que no haya ya un User con ese username
            if User.objects.filter(username=ident).exists():
                # Si quieres ser más estricto, puedes lanzar ValidationError en vez de reutilizar
                raise forms.ValidationError(
                    f"Ya existe un usuario con el nombre de usuario {ident}."
                )

            user = User.objects.create_user(
                username=ident,
                password="GinGaby2025",
                first_name=estudiante.nombres,
                last_name=estudiante.apellidos,
                email=estudiante.correo or "",
            )

            # Grupo Estudiante
            grupo, _ = Group.objects.get_or_create(name="Estudiante")
            user.groups.add(grupo)

            # Vincular al modelo Estudiante
            estudiante.user = user
            estudiante.save()

            # Crear Perfil con los datos del estudiante
            PerfilUsuario.objects.get_or_create(
                user=user,
                defaults={
                    "fecha_nacimiento": estudiante.fecha_nacimiento,
                    "telefono": estudiante.telefono,
                    "direccion": estudiante.direccion,
                    "foto": estudiante.foto,
                }
            )

        return estudiante

class DocenteForm(forms.ModelForm):
    class Meta:
        model = Docente
        # 👇 OJO: quitamos "usuario"
        fields = ["nombres", "apellidos", "identificacion",
                  "correo", "telefono", "curso_asignado", "foto"]
        widgets = {
            "nombres": forms.TextInput(attrs={"class": "form-input"}),
            "apellidos": forms.TextInput(attrs={"class": "form-input"}),
            "identificacion": forms.TextInput(attrs={"class": "form-input"}),
            "correo": forms.EmailInput(attrs={"class": "form-input"}),
            "telefono": forms.TextInput(attrs={"class": "form-input"}),
            "curso_asignado": forms.Select(attrs={"class": "form-select"}),
            "foto": forms.ClearableFileInput(attrs={"class": "form-input"}),
        }

    def clean_identificacion(self):
        identificacion = (self.cleaned_data.get("identificacion") or "").strip()
        qs = Docente.objects.filter(identificacion=identificacion)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un docente con esa identificación.")
        return identificacion

    def save(self, commit=True):
        """
        - Guarda el Docente
        - Si no tiene usuario asociado, crea:
            - User con:
                username = identificación
                password = GinGaby2025
            - Grupo 'Docente'
            - Perfil con telefono y foto (lo que tenemos en Docente)
        """
        docente = super().save(commit=False)

        creando = docente.pk is None

        if commit:
            docente.save()

        if creando and docente.usuario is None:
            ident = docente.identificacion.strip()

            if User.objects.filter(username=ident).exists():
                raise forms.ValidationError(
                    f"Ya existe un usuario con el nombre de usuario {ident}."
                )

            user = User.objects.create_user(
                username=ident,
                password="GinGaby2025",
                first_name=docente.nombres,
                last_name=docente.apellidos,
                email=docente.correo or "",
            )

            grupo, _ = Group.objects.get_or_create(name="Docente")
            user.groups.add(grupo)

            docente.usuario = user
            docente.save()

            # Crear Perfil para el docente (solo tenemos teléfono y foto aquí)
            PerfilUsuario.objects.get_or_create(
                user=user,
                defaults={
                    "telefono": docente.telefono,
                    "foto": docente.foto,
                    # "direccion" y "fecha_nacimiento" las puedes agregar luego manualmente
                }
            )

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
        fields = ["oferta", "periodo", "titulo", "descripcion", "peso"]
        widgets = {
            "oferta": forms.Select(attrs={"class": "form-select"}),
            "periodo": forms.Select(attrs={"class": "form-select"}),
            "titulo": forms.TextInput(attrs={"class": "form-input", "placeholder": "Comprende la suma y resta..." }),
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