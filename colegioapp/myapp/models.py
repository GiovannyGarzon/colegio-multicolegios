from django.db import models

class School(models.Model):
    name = models.CharField("Nombre del colegio", max_length=200)
    domain = models.CharField(
        "Dominio",
        max_length=200,
        unique=True,
        help_text="Ej: giongabi.edu.co, 127.0.0.1, localhost"
    )
    logo = models.ImageField("Logo", upload_to="logos/")
    sello = models.ImageField(
        "Sello institucional",
        upload_to="sellos/",
        null=True,
        blank=True,
        help_text="Sello oficial para certificados (marca de agua o firma)"
    )

    slogan = models.CharField(
        "Slogan",
        max_length=300,
        blank=True,
        help_text="Ej: EDUCANDO CON AMOR A QUIENES CONSTRUIRÁN EL MAÑANA"
    )

    # COLORES
    primary_color = models.CharField("Color primario", max_length=20, default="#0055AA")
    secondary_color = models.CharField("Color secundario", max_length=20, default="#FFFFFF")
    button_color = models.CharField("Color de botones", max_length=20, default="#00695C")
    background_color = models.CharField("Color de fondo", max_length=20, default="#F4F8F6")

    # MISIÓN / VISIÓN
    mission = models.TextField("Misión", blank=True)
    vision = models.TextField("Visión", blank=True)

    address = models.CharField("Dirección", max_length=250, blank=True)
    phone = models.CharField("Teléfono", max_length=20, blank=True)

    class Meta:
        verbose_name = "Colegio"
        verbose_name_plural = "Colegios"

    def __str__(self):
        return self.name
