from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm

from .models import PerfilUsuario


class UsuarioCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)
    grupos = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Roles / Grupos"
    )
    is_staff = forms.BooleanField(
        required=False,
        label='Acceso al panel administrativo'
    )

    foto = forms.ImageField(
        required=False,
        label="Foto (tipo carné)",
        help_text="Foto vertical, tipo carné. Formatos: JPG o PNG."
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'is_active', 'is_staff', 'grupos',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Opcional: estilo Bootstrap / clases CSS aquí

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()

            # grupos
            grupos = self.cleaned_data.get('grupos')
            if grupos is not None:
                user.groups.set(grupos)

            # perfil + foto
            foto = self.cleaned_data.get('foto')
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            if foto:
                perfil.foto = foto
            perfil.save()

        return user


class UsuarioUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    grupos = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Roles / Grupos"
    )
    is_staff = forms.BooleanField(
        required=False,
        label='Acceso al panel administrativo'
    )

    foto = forms.ImageField(
        required=False,
        label="Foto (tipo carné)",
        help_text="Foto vertical, tipo carné. Formatos: JPG o PNG."
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'is_active', 'is_staff', 'grupos',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # precargar grupos del usuario
        if self.instance.pk:
            self.fields['grupos'].initial = self.instance.groups.all()

            # precargar ayuda de foto si ya tiene
            try:
                perfil = self.instance.perfil
                if perfil.foto:
                    self.fields['foto'].help_text = "Foto actual cargada. Sube una nueva para reemplazarla."
            except PerfilUsuario.DoesNotExist:
                pass

    def clean_username(self):
        """
        Evitar el error de 'usuario ya existe' cuando es el mismo usuario.
        """
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe otro usuario con este nombre.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()

            # grupos
            grupos = self.cleaned_data.get('grupos')
            if grupos is not None:
                user.groups.set(grupos)

            # perfil + foto
            foto = self.cleaned_data.get('foto')
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            if foto:
                perfil.foto = foto  # reemplaza la anterior
            perfil.save()

        return user