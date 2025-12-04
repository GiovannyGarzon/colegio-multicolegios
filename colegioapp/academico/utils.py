from decimal import Decimal
from collections import defaultdict
from academico.models import (
    AsignaturaOferta,
    Periodo,
    Estudiante,
    CalificacionLogro,
    Logro,
)

def _promedio_asignatura_periodo(estudiante, oferta, periodo):
    """
    Promedio de UN estudiante en UNA asignatura y UN período,
    usando los logros ponderados (igual que en tu boletín).
    """
    logros = Logro.objects.filter(oferta=oferta, periodo=periodo).order_by("titulo")
    cals = (
        CalificacionLogro.objects
        .filter(estudiante=estudiante, logro__in=logros)
        .select_related("logro")
    )

    notas_por_logro = {c.logro_id: c.nota for c in cals}

    suma_pesada = Decimal("0")
    suma_pesos = Decimal("0")

    for lg in logros:
        nota = notas_por_logro.get(lg.id)
        if nota is not None:
            peso = lg.peso / Decimal("100")
            suma_pesada += Decimal(nota) * peso
            suma_pesos += peso

    if suma_pesos > 0:
        return (suma_pesada / suma_pesos).quantize(Decimal("0.01"))

    return None

def promedio_general_estudiante_periodo(estudiante, anio, curso, periodo):
    """
    Calcula el promedio general del estudiante en ese período,
    promediando todas las asignaturas del curso.
    """
    ofertas = AsignaturaOferta.objects.filter(anio=anio, curso=curso)
    notas = []

    for of in ofertas:
        p = _promedio_asignatura_periodo(estudiante, of, periodo)
        if p is not None:
            notas.append(p)

    if not notas:
        return None

    return (sum(notas) / len(notas)).quantize(Decimal("0.01"))

def ranking_curso_periodo(anio, curso, periodo):
    """
    Devuelve un dict {estudiante_id: puesto} ordenando de mayor a menor promedio.
    Usa ranking con empates (misma nota = mismo puesto).
    """
    estudiantes = Estudiante.objects.filter(curso=curso)
    lista = []

    for est in estudiantes:
        prom = promedio_general_estudiante_periodo(est, anio, curso, periodo)
        if prom is not None:
            lista.append((est.id, prom))

    lista.sort(key=lambda x: x[1], reverse=True)

    puestos = {}
    puesto_actual = 0
    ultimo_prom = None

    for idx, (est_id, prom) in enumerate(lista, start=1):
        if ultimo_prom is None or prom < ultimo_prom:
            puesto_actual = idx
        puestos[est_id] = puesto_actual
        ultimo_prom = prom

    return puestos

def ranking_curso_anual(anio, curso):
    estudiantes = Estudiante.objects.filter(curso=curso)
    lista = []

    periodos = Periodo.objects.filter(anio=anio).order_by("numero")[:3]

    for est in estudiantes:
        notas = []
        for per in periodos:
            prom = promedio_general_estudiante_periodo(est, anio, curso, per)
            if prom is not None:
                notas.append(prom)

        if not notas:
            continue

        prom_anual = (sum(notas) / len(notas)).quantize(Decimal("0.01"))
        lista.append((est.id, prom_anual))

    lista.sort(key=lambda x: x[1], reverse=True)

    puestos = {}
    puesto_actual = 0
    ultimo_prom = None

    for idx, (est_id, prom) in enumerate(lista, start=1):
        if ultimo_prom is None or prom < ultimo_prom:
            puesto_actual = idx
        puestos[est_id] = puesto_actual
        ultimo_prom = prom

    return puestos
