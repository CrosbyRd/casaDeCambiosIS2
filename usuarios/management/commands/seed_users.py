from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.models import Permission
from roles.models import Role

class Command(BaseCommand):
    help = "Crea/actualiza un usuario Administrador con rol y permisos"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        self.stdout.write(self.style.SUCCESS("Iniciando creación de usuario Administrador..."))

        # --- Crear usuario admin de la app ---
        email = "globalexchangea2@gmail.com"
        password = "password123"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": "Admin",
                "last_name": "Principal",
                "is_staff": True,     # puede loguearse como staff
                "is_superuser": False, # no es superusuario global
                "is_active": True,
                "is_verified": True,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Usuario creado: {email}"))
        else:
            self.stdout.write(self.style.WARNING(f"Usuario ya existía: {email}"))

        # --- Crear Rol Administrador ---
        rol_admin, _ = Role.objects.get_or_create(
            name="Administrador",
            defaults={"description": "Rol de Administrador"}
        )

        # --- Buscar permisos personalizados ---

        permisos_codenames = [
                "access_admin_dashboard",   # Panel Admin
                "access_cotizaciones",      # Cotizaciones
                "access_monedas_section",   # Monedas
                "access_roles_panel",       # NUEVO: acceso a Roles
                "delete_roles",             # NUEVO: eliminar Roles
            ]

        permisos = []
        for codename in permisos_codenames:
            try:
                perm = Permission.objects.get(codename=codename)
                permisos.append(perm)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"El permiso '{codename}' no existe. "
                    f"Ejecuta 'makemigrations' y 'migrate' en la app correspondiente primero."
                ))

        # Asignar permisos al rol
        if permisos:
            rol_admin.permissions.add(*permisos)
            rol_admin.save()

        # Asignar rol al usuario
        user.roles.add(rol_admin)

        self.stdout.write(self.style.SUCCESS(
            f"Usuario {email} asignado al rol Administrador con permisos {[p.codename for p in permisos]}."
        ))
