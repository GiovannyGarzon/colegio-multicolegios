from datetime import date
from .models import CuentaPorCobrar, AnioEconomico

def estudiante_tiene_deuda_bloqueante(estudiante):
    hoy = date.today()
    return CuentaPorCobrar.objects.filter(
        estudiante=estudiante,
        pagada=False,
        saldo_pendiente__gt=0,          # hay saldo por pagar
        concepto__bloquea_boletin=True, # solo conceptos marcados como bloqueantes (pensión, matrícula...)
        fecha_vencimiento__lt=hoy,      # la fecha de vencimiento ya pasó (por ejemplo, día 6)
    ).exists()