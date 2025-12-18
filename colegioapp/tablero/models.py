from django.db import models
from django.contrib.auth.models import User
from academico.models import Estudiante, CalificacionLogro, Observador
from myapp.models import School

class Noticia(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    resumen = models.TextField(blank=True)               # opcional: texto corto
    cuerpo = models.TextField()                          # texto completo
    imagen = models.ImageField(upload_to='tablero/', blank=True, null=True)
    activo = models.BooleanField(default=True)           # solo las activas salen en el tablero
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    publicado_por = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Mantener máximo 5 noticias activas
        activas = Noticia.objects.filter(activo=True).order_by('-fecha_publicacion')
        exceso = activas[5:]   # de la 6 en adelante
        if exceso:
            # Opción A: archivar (no borrar)
            exceso.update(activo=False)
            # Opción B si prefieres borrar: for n in exceso: n.delete()db import models


