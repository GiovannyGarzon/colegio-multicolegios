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

TRIMESTRES = {
    1: {
        "meses": [2, 3, 4],          # Febrero, Marzo, Abril
        "deadline": (5, 10),         # 10 de mayo
        "check_all_concepts": False,
    },
    2: {
        "meses": [5, 6, 7, 8],       # Mayo, Junio, Julio, Agosto
        "deadline": (9, 10),         # 10 de septiembre (ejemplo)
        "check_all_concepts": False,
    },
    3: {
        "meses": [9, 10, 11],        # Sept, Oct, Nov
        "deadline": (12, 10),        # 10 de diciembre (ejemplo)
        # aquí se exige estar al día EN TODO concepto del año
        "check_all_concepts": True,
    },
}

def resumen_cartera_para_boletin(estudiante, anio: AnioEconomico, trimestre: int):
    """
    Devuelve si el estudiante puede ver el boletín de ese trimestre
    y el detalle de lo que debe.
    """
    conf = TRIMESTRES[trimestre]
    year_int = int(anio.nombre)  # asumiendo anio.nombre = "2025"

    dl_month, dl_day = conf["deadline"]
    deadline = date(year_int, dl_month, dl_day)
    hoy = date.today()

    # Deudas de los meses del trimestre, cualquier concepto de ese año
    deudas_trimestre = CuentaPorCobrar.objects.filter(
        estudiante=estudiante,
        concepto__anio=anio,
        mes__in=conf["meses"],
        saldo_pendiente__gt=0,
        pagada=False,
    )

    # Para 3er trimestre: revisar deudas en TODO concepto del año
    deudas_otros = CuentaPorCobrar.objects.none()
    if conf.get("check_all_concepts"):
        deudas_otros = (
            CuentaPorCobrar.objects
            .filter(
                estudiante=estudiante,
                concepto__anio=anio,
                saldo_pendiente__gt=0,
                pagada=False,
            )
        )

    tiene_deudas_trimestre = deudas_trimestre.exists()
    tiene_deudas_otros = deudas_otros.exists()

    total_pendiente = (
        deudas_trimestre.aggregate(total=Sum("saldo_pendiente"))["total"] or 0
    )
    if conf.get("check_all_concepts"):
        total_pendiente += (
            deudas_otros.aggregate(total=Sum("saldo_pendiente"))["total"] or 0
        )

    puede_ver = True
    motivo = ""

    if hoy > deadline and (tiene_deudas_trimestre or tiene_deudas_otros):
        puede_ver = False
        motivo = "Presenta obligaciones económicas pendientes para este trimestre."

    return {
        "puede_ver": puede_ver,
        "deadline": deadline,
        "deudas_trimestre": deudas_trimestre,
        "deudas_otros": deudas_otros,
        "total_pendiente": total_pendiente,
        "motivo": motivo,
    }