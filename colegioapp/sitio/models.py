from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator

from myapp.models import School  # <- AJUSTA AQUÍ si tu app se llama distinto

class HomeHeroSlide(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="hero_slides")
    image = models.ImageField(upload_to="public/hero/")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # opcional: por si luego quieres textos por slide
    # caption = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Slide Hero (Home)"
        verbose_name_plural = "Slides Hero (Home)"

    def __str__(self):
        return f"{self.school.name} - Slide #{self.order}"

class AboutSlide(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="about_slides"
    )
    title = models.CharField("Título (opcional)", max_length=200, blank=True)
    image = models.ImageField(upload_to="about/slides/")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Slide Nosotros"
        verbose_name_plural = "Slides Nosotros"

    def __str__(self):
        return f"{self.school.name} - Slide {self.order}"

class PublicPage(models.Model):
    """
    Página pública por colegio y slug: home, nosotros, admisiones, contacto
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="public_pages")
    slug = models.SlugField(max_length=50)  # home, nosotros, admisiones, contacto
    title = models.CharField(max_length=200, blank=True)
    subtitle = models.CharField(max_length=300, blank=True)
    hero_video = models.FileField(upload_to="public/videos/", blank=True, null=True)
    hero_video_poster = models.ImageField(upload_to="public/videos/posters/", blank=True, null=True)

    # Banner superior (imagen grande)
    banner = models.ImageField(upload_to="public/banners/", blank=True, null=True)

    # Texto principal (simple). Si luego quieres HTML, lo cambiamos.
    content = models.TextField(blank=True)

    # CTA opcional (botón)
    cta_text = models.CharField(max_length=60, blank=True)
    cta_url = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("school", "slug")
        verbose_name = "Página pública"
        verbose_name_plural = "Páginas públicas"

    def __str__(self):
        return f"{self.school.name} - {self.slug}"


class HomeBlock(models.Model):
    """
    Bloques/tarjetas del Home (Proyecto, Ruta escolar, etc.)
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="home_blocks")
    title = models.CharField(max_length=150)
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to="public/blocks/", blank=True, null=True)

    button_text = models.CharField(max_length=60, blank=True)
    button_url = models.CharField(max_length=300, blank=True)  # puede ser /admisiones/ o https://...

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Bloque Home"
        verbose_name_plural = "Bloques Home"

    def __str__(self):
        return f"{self.school.name} - {self.title}"


class NewsPost(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="news_posts")
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="public/news/", blank=True, null=True)

    published_at = models.DateTimeField(default=timezone.now)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"

    def __str__(self):
        return f"{self.school.name} - {self.title}"


class SchoolPublicConfig(models.Model):
    """
    Config extra del sitio público que NO tenías en School:
    redes, mapa, whatsapp, horarios.
    (1 por colegio)
    """
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name="public_config")

    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r"^\+?\d{7,15}$", "Usa solo números, opcional +")]
    )
    email_public = models.EmailField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    schedule_text = models.CharField(max_length=250, blank=True)  # "L-V 7am-4pm / S 8am-12m"
    map_iframe = models.TextField(blank=True)  # pegar iframe de Google Maps

    class Meta:
        verbose_name = "Config sitio público"
        verbose_name_plural = "Config sitios públicos"

    def __str__(self):
        return f"Config público - {self.school.name}"