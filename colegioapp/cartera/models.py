from django.db import models
from academico.models import *
# Create your models here.
from myapp.models import School


class AnioEconomico(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="anios_economicos",
        null=True,  # lo dejamos así por la migración inicial
        blank=True
    )
    nombre = models.CharField(max_length=20, unique=True)  # Ej: "2025"
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class ConceptoPago(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="conceptos_pago",
        null=True,
        blank=True
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    anio = models.ForeignKey(AnioEconomico, on_delete=models.CASCADE, related_name='conceptos')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    recurrente = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    bloquea_boletin = models.BooleanField(
        default=True,
        help_text="Si hay deuda vencida de este concepto, bloquea el boletín del estudiante."
    )

    def __str__(self):
        return f"{self.nombre} ({self.anio})"


class CuentaPorCobrar(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="cuentas_cobrar",
        null=True,
        blank=True
    )
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='cuentas')
    concepto = models.ForeignKey(ConceptoPago, on_delete=models.CASCADE)
    fecha_generacion = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    saldo_pendiente = models.DecimalField(max_digits=10, decimal_places=2)
    pagada = models.BooleanField(default=False)
    mes = models.PositiveSmallIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.estudiante} - {self.concepto.nombre} ({self.concepto.anio})"

    @property
    def nombre_mes(self):
        if not self.mes:
            return ""
        meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        return meses[self.mes]


class Pago(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="pagos",
        null=True,
        blank=True
    )
    cuenta = models.ForeignKey(CuentaPorCobrar, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField(auto_now_add=True)
    valor_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    medio_pago = models.CharField(max_length=50)  # libre, lo llenas desde el HTML
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Pago {self.valor_pagado} - {self.cuenta.estudiante}"