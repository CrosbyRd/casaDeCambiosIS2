# usuarios/management/commands/seed_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from roles.models import Role

class Command(BaseCommand):
    help = "Crea/actualiza usuarios iniciales y asigna roles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Borra todos los usuarios (excepto superusuarios) antes de sembrar."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        self.stdout.write(self.style.SUCCESS("Iniciando la creación de usuarios iniciales..."))

        # Opcional: limpiar usuarios (mantiene superusers)
        if options.get("reset"):
            deleted, _ = User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.WARNING(f"Usuarios eliminados (no superusers): {deleted}"))

        # Usuarios semilla (ajusta lo que necesites)
        seeds = [
            {
                "email": "admin@casadecambio.com",
                "password": "password123",
                "first_name": "Admin",
                "last_name": "Principal",
                "roles": ["ADMINISTRADOR"],
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "is_verified": True,
            },
            {
                "email": "analista1@casadecambio.com",
                "password": "password123",
                "first_name": "Juan",
                "last_name": "Pérez",
                "roles": ["ANALISTA"],
                "is_active": True,
            },
            {
                "email": "cliente@example.com",
                "password": "password123",
                "first_name": "Ana",
                "last_name": "García",
                "roles": ["CLIENTE"],
                "is_active": True,
            },
            {
                "email": "lclc@mgail.com",
                "password": "ttu789",
                "first_name": "Lope",
                "last_name": "GGG",
                "roles": ["CLIENTE"],
                "is_active": True,
            },
        ]

        for data in seeds:
            roles = data.pop("roles", [])
            email = data["email"].lower()

            # Crear si no existe, si existe, actualizar campos relevantes
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": data.get("first_name", ""),
                    "last_name": data.get("last_name", ""),
                    "is_staff": data.get("is_staff", False),
                    "is_superuser": data.get("is_superuser", False),
                    "is_active": data.get("is_active", True),
                    "is_verified": data.get("is_verified", True),
                },
            )

            if created:
                user.set_password(data["password"])
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Creado: {email}"))
            else:
                changed = False
                for field in ["first_name", "last_name", "is_staff", "is_superuser", "is_active", "is_verified"]:
                    if field in data and getattr(user, field) != data[field]:
                        setattr(user, field, data[field])
                        changed = True
                if "password" in data and data["password"]:
                    user.set_password(data["password"])
                    changed = True
                if changed:
                    user.save()
                    self.stdout.write(self.style.WARNING(f"Actualizado: {email}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Ya existe: {email} (sin cambios)"))

            # Asignar roles (se crean si no existen)
            for role_name in roles:
                role, _ = Role.objects.get_or_create(name=role_name)
                user.roles.add(role)

        self.stdout.write(self.style.SUCCESS("Seeding terminado."))
