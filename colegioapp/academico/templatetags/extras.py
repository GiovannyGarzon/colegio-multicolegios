from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None

@register.filter
def prom_color(value):
    """
    Retorna la clase CSS según el rango del promedio.
    """
    try:
        v = float(value)
    except:
        return ""

    if v < 3.0:
        return "prom-rojo"
    elif 3.0 <= v < 3.9:
        return "prom-amarillo"
    elif 3.9 <= v < 4.4:
        return "prom-naranja"
    else:
        return "prom-verde"