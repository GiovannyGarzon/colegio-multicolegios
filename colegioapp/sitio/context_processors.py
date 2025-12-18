from .models import SchoolPublicConfig

def public_config(request):
    school = getattr(request, "school", None) or getattr(request, "colegio_actual", None)
    config = SchoolPublicConfig.objects.filter(school=school).first() if school else None
    return {"config": config}