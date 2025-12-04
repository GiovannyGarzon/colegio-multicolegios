from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from .models import Docente


@receiver(post_save, sender=Docente)
def crear_usuario_para_docente(sender, instance, created, **kwargs):
    """
    Crea automáticamente un usuario para el Docente recién creado,
    lo asigna al grupo 'Docente' y lo vincula al campo instance.usuario.
    """

    # Solo al crear, y solo si todavía no tiene usuario
    if created and not instance.usuario:
        # Username base: la identificación
        username = instance.identificacion

        if not username:
            # Si por alguna razón no tiene identificación, inventamos uno básico
            base = "docente"
        else:
            base = username

        # Aseguramos que el username sea único
        original = base
        contador = 1
        while User.objects.filter(username=base).exists():
            base = f"{original}_{contador}"
            contador += 1

        email = instance.correo or ""
        first_name = instance.nombres
        last_name = instance.apellidos

        # Crear usuario con contraseña = identificación (puedes cambiar esto luego)
        password = instance.identificacion or "docente123"

        user = User.objects.create_user(
            username=base,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
        )

        # Asignar grupo Docente
        grupo_docente, _ = Group.objects.get_or_create(name="Docente")
        grupo_docente.user_set.add(user)

        # Vincular al Docente SIN disparar de nuevo el post_save
        Docente.objects.filter(pk=instance.pk).update(usuario=user)

    # Opcional: si quieres que al editar el Docente se actualicen datos del User:
    elif not created and instance.usuario:
        user = instance.usuario
        cambiado = False

        if user.first_name != instance.nombres:
            user.first_name = instance.nombres
            cambiado = True

        if user.last_name != instance.apellidos:
            user.last_name = instance.apellidos
            cambiado = True

        if instance.correo and user.email != instance.correo:
            user.email = instance.correo
            cambiado = True

        if cambiado:
            user.save()