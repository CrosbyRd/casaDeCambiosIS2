import json
import uuid
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
import json
import uuid
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from roles.models import Role
from clientes.models import Cliente

class Command(BaseCommand):
    help = "Crea o actualiza usuarios de ejemplo (Admin, Analista y Clientes) y los asocia a sus roles."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        self.stdout.write(self.style.SUCCESS("Iniciando creación y asignación de roles para usuarios de ejemplo..."))

        # --- Obtener Roles (creados por seed_roles) ---
        try:
            rol_admin = Role.objects.get(name="Administrador")
            rol_cliente = Role.objects.get(name="Cliente")
            rol_cliente_dev_otp_bypass = Role.objects.get(name="Cliente_Dev_OTP_Bypass")
            rol_analista = Role.objects.get(name="Analista")
        except Role.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(f"Error: Rol no encontrado - {e}. Asegúrate de ejecutar 'python manage.py seed_roles' primero."))
            return

        # --- Usuario Administrador ---
        admin_email = "globalexchangea2@gmail.com"
        admin_password = "password123"
        admin_user, created = User.objects.update_or_create(
            email=admin_email,
            defaults={
                "first_name": "Admin",
                "last_name": "Principal",
                "is_staff": True,
                "is_superuser": False,
                "is_active": True,
                "is_verified": True,
            },
        )
        admin_user.set_password(admin_password)
        admin_user.save()
        admin_user.roles.add(rol_admin)
        self.stdout.write(self.style.SUCCESS(f"Usuario Administrador '{admin_email}' asegurado y asignado al rol 'Administrador'."))

        # --- Usuario Analista ---
        analista_email = "analista1@example.com"
        analista_password = "password123"
        analista_user, created = User.objects.update_or_create(
            email=analista_email,
            defaults={
                "first_name": "Analista",
                "last_name": "Cambiario",
                "is_staff": False,
                "is_superuser": False,
                "is_active": True,
                "is_verified": True,
            },
        )
        analista_user.set_password(analista_password)
        analista_user.save()
        analista_user.roles.add(rol_analista)
        analista_user.roles.add(rol_cliente_dev_otp_bypass) # Para pruebas
        self.stdout.write(self.style.SUCCESS(f"Usuario Analista '{analista_email}' asegurado y asignado al rol 'Analista'."))

        # --- Cargar fixture de clientes y crear usuarios asociados ---
        project_root = Path(__file__).resolve().parents[3]
        fixture_path = project_root / "clientes" / "fixtures" / "clientes.json"
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"Fixture de clientes no encontrado en: {fixture_path}"))
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            clientes_data = json.load(f)

        for item in clientes_data:
            if item.get("model") != "clientes.cliente":
                continue

            fields = item["fields"]
            cliente, _ = Cliente.objects.update_or_create(
                nombre=fields["nombre"],
                defaults={
                    "categoria": fields["categoria"],
                    "activo": fields["activo"],
                }
            )

            # Crear usuario para este cliente
            client_user_email = f"{fields['nombre'].lower().replace(' ', '')}@example.com"
            client_user_password = "password123"
            client_user, created = User.objects.update_or_create(
                email=client_user_email,
                defaults={
                    "first_name": fields["nombre"].split(' ')[0],
                    "last_name": fields["nombre"].split(' ')[-1] if len(fields["nombre"].split(' ')) > 1 else "",
                    "is_staff": False,
                    "is_superuser": False,
                    "is_active": True,
                    "is_verified": True,
                },
            )
            client_user.set_password(client_user_password)
            client_user.save()
            
            # Asociar usuario con cliente y roles
            client_user.clientes.add(cliente)
            client_user.roles.add(rol_cliente)
            client_user.roles.add(rol_cliente_dev_otp_bypass)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"Usuario para cliente '{cliente.nombre}' creado y roles asignados."))
            else:
                self.stdout.write(self.style.WARNING(f"Usuario para cliente '{cliente.nombre}' actualizado y roles asignados."))

        self.stdout.write(self.style.SUCCESS("Proceso de creación de usuarios de ejemplo finalizado."))
