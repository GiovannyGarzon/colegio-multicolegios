from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from academico.models import Estudiante

class Command(BaseCommand):
    help = "Crea/relaciona usuarios (grupo Estudiante) para cada Estudiante."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="GinGaby2025*", help="Contraseña inicial.")

    def handle(self, *args, **opts):
        grupo, _ = Group.objects.get_or_create(name="Estudiante")
        pwd = opts["password"]
        creados, vinculados = 0, 0

        for est in Estudiante.objects.all():
            if est.user and est.user.is_active:
                continue
            username = est.identificacion
            user, created = User.objects.get_or_create(username=username, defaults={
                "first_name": est.nombres.split()[0],
                "last_name": est.apellidos,
                "email": est.correo or "",
            })
            if created:
                user.set_password(pwd)
                user.save()
                user.groups.add(grupo)
                creados += 1
            est.user = user
            est.save()
            vinculados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Usuarios creados: {creados} · Estudiantes vinculados: {vinculados}"
        ))