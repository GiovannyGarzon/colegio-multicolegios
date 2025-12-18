from django.db import models
from django.contrib.auth.models import User
from myapp.models import School


class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    foto = models.ImageField(upload_to="usuarios/", null=True, blank=True)

    def __str__(self):
        # usando school, con fallback por si está vacío
        return f"Perfil de {self.user.username} ({self.school or 'sin colegio'})"


