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

        # --- Crear/actualizar usuario admin de la app (sin superusuario) ---
        email = "globalexchangea2@gmail.com"
        password = "password123"

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": "Admin",
                "last_name": "Principal",
                "is_staff": True,
                "is_superuser": False,
                "is_active": True,
                "is_verified": True,
            },
        )
        # asegurar/actualizar campos base
        changed = False
        for k, v in {
            "first_name": "Admin",
            "last_name": "Principal",
            "is_staff": True,
            "is_superuser": False,
            "is_active": True,
            "is_verified": True,
        }.items():
            if getattr(user, k) != v:
                setattr(user, k, v)
                changed = True
        if changed:
            user.save()

        # (re)establecer contraseña
        if password:
            user.set_password(password)
            user.save()

        self.stdout.write(self.style.SUCCESS(f"Usuario preparado: {email}"))

        # --- Crear/actualizar Rol Administrador ---
        rol_admin, _ = Role.objects.get_or_create(
            name="Administrador",
            defaults={"description": "Rol de Administrador"}
        )

        # --- Permisos requeridos por el panel + TED ---
        # Usamos (app_label, codename) para evitar colisiones entre apps.
        permisos_requeridos = [
            ("admin_panel", "access_admin_dashboard"),
            ("cotizaciones", "access_cotizaciones"),
            ("monedas", "access_monedas_section"),
            ("roles", "access_roles_panel"),
            ("roles", "delete_roles"),
            ("usuarios", "access_user_client_management"),
            ("clientes", "access_clientes_panel"),
            # NUEVOS
            ("ted", "puede_operar_terminal"),
            ("monedas", "access_ted_inventory"),
        ]

        permisos_ok = []
        faltantes = []
        for app_label, codename in permisos_requeridos:
            try:
                perm = Permission.objects.get(
                    codename=codename,
                    content_type__app_label=app_label
                )
                permisos_ok.append(perm)
            except Permission.DoesNotExist:
                faltantes.append(f"{app_label}.{codename}")

        if faltantes:
            self.stdout.write(self.style.ERROR(
                "Faltan permisos (probablemente migraciones no aplicadas):\n  - " +
                "\n  - ".join(faltantes) +
                "\nEjecuta: python manage.py makemigrations monedas ted && python manage.py migrate"
            ))

        if permisos_ok:
            rol_admin.permissions.add(*permisos_ok)
            rol_admin.save()

        # --- Asignar rol al usuario (idempotente) ---
        user.roles.add(rol_admin)

        self.stdout.write(self.style.SUCCESS(
            f"Usuario {email} asignado al rol Administrador con permisos: "
            + ", ".join([f"{p.content_type.app_label}.{p.codename}" for p in permisos_ok])
        ))
