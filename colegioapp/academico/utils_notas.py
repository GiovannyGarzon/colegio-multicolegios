from decimal import Decimal
from academico.models import Actividad, CalificacionActividad, CalificacionLogro, Logro

def recalcular_nota_logro_desde_actividades(estudiante, logro):
    if logro.tipo != Logro.TIPO_HACER:
        return

    actividades = Actividad.objects.filter(logro=logro)
    if not actividades.exists():
        CalificacionLogro.objects.filter(estudiante=estudiante, logro=logro).delete()
        return

    cals = CalificacionActividad.objects.filter(
        actividad__in=actividades,
        estudiante=estudiante,
    ).select_related("actividad")

    if not cals.exists():
        CalificacionLogro.objects.filter(estudiante=estudiante, logro=logro).delete()
        return

    pesos = [c.actividad.peso for c in cals if c.actividad.peso]
    suma_pesos = sum(pesos) if pesos else Decimal("0")
    nota_final = None

    if suma_pesos == Decimal("100"):
        suma_pesada = Decimal("0")
        for c in cals:
            if c.nota is not None:
                peso_rel = c.actividad.peso / Decimal("100")
                suma_pesada += Decimal(c.nota) * peso_rel
        nota_final = suma_pesada
    else:
        notas = [c.nota for c in cals if c.nota is not None]
        if notas:
            nota_final = (sum(notas) / len(notas)).quantize(Decimal("0.01"))

    if nota_final is None:
        CalificacionLogro.objects.filter(estudiante=estudiante, logro=logro).delete()
    else:
        CalificacionLogro.objects.update_or_create(
            estudiante=estudiante,
            logro=logro,
            defaults={"nota": nota_final},
        )