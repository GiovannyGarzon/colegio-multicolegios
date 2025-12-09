from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.contrib.auth.models import User

class Curso(models.Model):
    nombre = models.CharField(max_length=100)
    grado = models.CharField(max_length=50)
    jornada = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.grado} - {self.nombre}"

class Docente(models.Model):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    identificacion = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    curso_asignado = models.ForeignKey(Curso, on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    foto = models.ImageField(upload_to='docentes/', null=True, blank=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

class Estudiante(models.Model):
    TIPO_DOC_CHOICES = [
        ("RC", "Registro civil"),
        ("TI", "Tarjeta de identidad"),
        ("CC", "Cédula de ciudadanía"),
    ]

    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    tipo_documento = models.CharField(
        max_length=2,
        choices=TIPO_DOC_CHOICES,
        default="RC",
        verbose_name="Tipo de documento",
    )
    identificacion = models.CharField(max_length=20, unique=True)
    fecha_nacimiento = models.DateField()
    direccion = models.CharField(max_length=150, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    curso = models.ForeignKey(Curso, on_delete=models.SET_NULL, null=True, blank=True)
    acudiente = models.CharField(max_length=100, blank=True, null=True)
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)
    foto = models.ImageField(upload_to='estudiantes/', null=True, blank=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

class AnioLectivo(models.Model):
    nombre = models.CharField(max_length=20, unique=True)  # "2025"
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Año lectivo"
        verbose_name_plural = "Años lectivos"
        ordering = ["-activo", "-nombre"]

    def __str__(self):
        return self.nombre


class Periodo(models.Model):
    anio = models.ForeignKey(AnioLectivo, on_delete=models.CASCADE, related_name="periodos")
    numero = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])  # 1..4
    nombre = models.CharField(max_length=50)  # "Periodo 1"
    peso = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("25.00"))  # % del año

    class Meta:
        unique_together = ("anio", "numero")
        ordering = ["anio__nombre", "numero"]

    def __str__(self):
        return f"{self.anio} - {self.nombre} ({self.peso}%)"


class AsignaturaCatalogo(models.Model):
    """
    Catálogo global de asignaturas (Matemáticas, Lengua, etc.).
    """
    nombre = models.CharField(max_length=120, unique=True)
    area = models.CharField(max_length=120, blank=True, null=True)  # opcional: Ciencias, Lenguaje...

    class Meta:
        verbose_name = "Asignatura (Catálogo)"
        verbose_name_plural = "Asignaturas (Catálogo)"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class AsignaturaOferta(models.Model):
    """
    Oferta concreta de una asignatura para un curso en un año lectivo.
    """
    anio = models.ForeignKey(AnioLectivo, on_delete=models.CASCADE, related_name="ofertas")
    curso = models.ForeignKey("academico.Curso", on_delete=models.CASCADE, related_name="ofertas")
    asignatura = models.ForeignKey(AsignaturaCatalogo, on_delete=models.CASCADE, related_name="ofertas")
    docente = models.ForeignKey("academico.Docente", on_delete=models.SET_NULL, null=True, blank=True)
    intensidad_horaria = models.PositiveIntegerField(default=0)  # horas/semana (opcional)

    class Meta:
        unique_together = ("anio", "curso", "asignatura")
        ordering = ["anio__nombre", "curso__grado", "curso__nombre", "asignatura__nombre"]

    def __str__(self):
        return f"{self.anio} | {self.curso} | {self.asignatura}"

class Logro(models.Model):
    TIPO_HACER = "HACER"
    TIPO_SER = "SER"
    TIPO_SABER = "SABER"

    TIPO_CHOICES = [
        (TIPO_HACER, "Saber hacer"),
        (TIPO_SER, "Saber ser"),
        (TIPO_SABER, "Saber"),
    ]

    oferta = models.ForeignKey(AsignaturaOferta, on_delete=models.CASCADE, related_name="logros")
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name="logros")

    # 👇 NUEVO
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default=TIPO_HACER,
        help_text="Clasificación: saber hacer / saber ser / saber."
    )

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    peso = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Porcentaje dentro del periodo. La suma por periodo debe ser 100%."
    )

class CalificacionLogro(models.Model):
    """
    Nota por estudiante para un logro específico.
    """
    estudiante = models.ForeignKey("academico.Estudiante", on_delete=models.CASCADE, related_name="calificaciones_logro")
    logro = models.ForeignKey(Logro, on_delete=models.CASCADE, related_name="calificaciones")
    nota = models.DecimalField(
        max_digits=4, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("5.00"))]
    )
    observaciones = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("estudiante", "logro")
        index_together = [["estudiante", "logro"]]

    def __str__(self):
        return f"{self.estudiante} | {self.logro} = {self.nota}"

class Observador(models.Model):
    estudiante = models.ForeignKey("academico.Estudiante", on_delete=models.CASCADE, related_name="observaciones")
    fecha = models.DateField(auto_now_add=True)
    tipo = models.CharField(max_length=40, choices=[
        ("POSITIVA","Positiva"),
        ("LLAMADO","Llamado de atención"),
        ("ACUERDO","Acuerdo con acudiente"),
    ])
    detalle = models.TextField()

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha} · {self.estudiante} · {self.get_tipo_display()}"

class ObservacionBoletin(models.Model):
    estudiante = models.ForeignKey(
        "academico.Estudiante",
        on_delete=models.CASCADE,
        related_name="observaciones_boletin",
    )
    periodo = models.ForeignKey(
        Periodo,
        on_delete=models.CASCADE,
        related_name="observaciones_boletin",
    )
    docente = models.ForeignKey(
        "academico.Docente",
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    texto = models.TextField()
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("estudiante", "periodo")
        verbose_name = "Observación de boletín"
        verbose_name_plural = "Observaciones de boletín"

    def __str__(self):
        return f"{self.estudiante} - {self.periodo} ({self.fecha_actualizacion:%Y-%m-%d})"

class PaseLista(models.Model):
    """
    Encabezado de asistencia de un curso en una fecha.
    Un registro por curso / fecha (y periodo/año).
    """
    anio = models.ForeignKey(AnioLectivo, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE)
    fecha = models.DateField()

    docente = models.ForeignKey(
        Docente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Docente que pasó la asistencia"
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        unique_together = ("curso", "fecha")
        ordering = ["-fecha"]

    def __str__(self):
        return f"Asistencia {self.curso} - {self.fecha}"


class AsistenciaDetalle(models.Model):
    """
    Detalle de asistencia por estudiante.
    """
    PRESENTE = "P"
    AUSENTE = "A"
    JUSTIFICADA = "J"
    TARDANZA = "T"

    ESTADOS = [
        (PRESENTE, "Presente"),
        (AUSENTE, "Ausente"),
        (JUSTIFICADA, "Ausencia justificada"),
        (TARDANZA, "Tardanza"),
    ]

    pase = models.ForeignKey(
        PaseLista,
        on_delete=models.CASCADE,
        related_name="detalles"
    )
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    estado = models.CharField(max_length=1, choices=ESTADOS, default=PRESENTE)
    observacion = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("pase", "estudiante")
        ordering = ["estudiante__apellidos", "estudiante__nombres"]

    def __str__(self):
        return f"{self.estudiante} - {self.get_estado_display()} - {self.pase.fecha}"

class Matricula(models.Model):
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name="matriculas"
    )
    anio = models.ForeignKey(
        AnioLectivo,
        on_delete=models.CASCADE,
        related_name="matriculas"
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name="matriculas"
    )
    fecha_matricula = models.DateField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("estudiante", "anio")
        ordering = ["-anio__nombre", "curso__grado", "curso__nombre"]

    def __str__(self):
        return f"{self.estudiante} - {self.anio.nombre} - {self.curso}"

class BloqueHorario(models.Model):
    LUNES = 1
    MARTES = 2
    MIERCOLES = 3
    JUEVES = 4
    VIERNES = 5

    DIAS_SEMANA = (
        (LUNES, "Lunes"),
        (MARTES, "Martes"),
        (MIERCOLES, "Miércoles"),
        (JUEVES, "Jueves"),
        (VIERNES, "Viernes"),
    )

    anio = models.ForeignKey(
        AnioLectivo,
        on_delete=models.CASCADE,
        related_name="bloques_horario",
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name="bloques_horario",
    )

    dia_semana = models.PositiveSmallIntegerField(choices=DIAS_SEMANA)

    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    # Clase normal
    oferta = models.ForeignKey(
        AsignaturaOferta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bloques_horario",
    )

    # Descanso u otra actividad
    es_receso = models.BooleanField(default=False)
    descripcion = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ej: Receso, Almuerzo, Actividad lúdica",
    )

    class Meta:
        ordering = ["dia_semana", "hora_inicio"]
        verbose_name = "Bloque de horario"
        verbose_name_plural = "Bloques de horario"

    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin} ({self.curso})"

class Actividad(models.Model):
    logro = models.ForeignKey(
        Logro,
        on_delete=models.CASCADE,
        related_name="actividades"
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha = models.DateField(null=True, blank=True)
    peso = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Porcentaje dentro del logro. Lo normal es que las actividades sumen 100%."
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.titulo} ({self.logro})"


class CalificacionActividad(models.Model):
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="calificaciones"
    )
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    nota = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("actividad", "estudiante")

    def __str__(self):
        return f"{self.estudiante} - {self.actividad} : {self.nota}"


class SaberSer(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    anio = models.ForeignKey(AnioLectivo, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE)
    asignatura_oferta = models.ForeignKey(AsignaturaOferta, on_delete=models.CASCADE)

    # 🔹 Nota FINAL (se sigue usando para los cálculos)
    nota = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    # 🔹 Detalle por dimensión
    nota_comportamiento = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    nota_responsabilidad = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    nota_autoevaluacion = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    observacion = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("estudiante", "periodo", "asignatura_oferta")