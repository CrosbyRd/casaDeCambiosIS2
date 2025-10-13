import json
import uuid
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from roles.models import Role
from clientes.models import Cliente
from ted.models import TedPerms  # <- para el ContentType del permiso TED


class Command(BaseCommand):
    help = "Crea/actualiza usuarios Administradores y Clientes con roles y permisos."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        self.stdout.write(self.style.SUCCESS("Iniciando creación de usuarios Administradores y Clientes..."))

        # --- Admin app ---
        admin_email = "globalexchangea2@gmail.com"
        admin_password = "password123"
        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "first_name": "Admin",
                "last_name": "Principal",
                "is_staff": True,
                "is_superuser": False,
                "is_active": True,
                "is_verified": True,
                "verification_code": None,
                "code_created_at": None,
            },
        )
        if created:
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Usuario Administrador creado: {admin_email}"))
        else:
            self.stdout.write(self.style.WARNING(f"Usuario Administrador ya existía: {admin_email}"))

        # Asegurar flags y password
        defaults = {
            "first_name": admin_user.first_name,
            "last_name": admin_user.last_name,
            "is_staff": True,
            "is_superuser": False,
            "is_active": admin_user.is_active,
            "is_verified": admin_user.is_verified,
            "verification_code": None,
            "code_created_at": None,
        }
        admin_user, _ = User.objects.update_or_create(email=admin_email, defaults=defaults)
        admin_user.set_password(admin_password)
        admin_user.save()

        # --- Rol Administrador ---
        rol_admin, _ = Role.objects.get_or_create(name="Administrador", defaults={"description": "Rol de Administrador"})

        # --- Permisos específicos de panel y TED ---
        faltantes = []
        permisos_admin_codenames = [
            "access_admin_dashboard",       # Panel Admin
            "access_cotizaciones",          # Cotizaciones
            "access_monedas_section",       # Monedas
            "access_roles_panel",           # Roles
            "delete_roles",                 # Roles
            "access_user_client_management",# Asociación cliente-usuario
            "access_clientes_panel",        # Clientes
            "access_medios_acreditacion",   # Medios de acreditación
            "access_pagos_section",         # Pagos
            "puede_operar_terminal",
            "puede_gestionar_inventario",
        ]

        permisos_admin = []
        for codename in permisos_admin_codenames:
            try:
                perm = Permission.objects.get(codename=codename)
                permisos_admin.append(perm)
            except Permission.DoesNotExist:
                faltantes.append(codename)

        # Permiso TED (propio de la app 'ted')
        ct_ted = ContentType.objects.get_for_model(TedPerms)
        perm_ted, _ = Permission.objects.get_or_create(
            codename="puede_operar_terminal",
            content_type=ct_ted,
            defaults={"name": "Puede operar el terminal TED"},
        )
        permisos_admin.append(perm_ted)

        # Asignar permisos al rol Administrador
        if permisos_admin:
            rol_admin.permissions.set(permisos_admin)
            rol_admin.save()

        # Rol Cliente
        rol_cliente, _ = Role.objects.get_or_create(
            name="Cliente", defaults={"description": "Rol de Cliente estándar para usuarios finales."}
        )
        rol_cliente_dev_otp_bypass, _ = Role.objects.get_or_create(
            name="Cliente_Dev_OTP_Bypass", defaults={"description": "Rol especial para clientes en desarrollo que salta el OTP."}
        )

        # Permisos genéricos del modelo Cliente
        cliente_ct = ContentType.objects.get_for_model(Cliente)
        permisos_cliente = list(Permission.objects.filter(content_type=cliente_ct))
        if permisos_cliente:
            rol_cliente.permissions.set(permisos_cliente)
            rol_cliente.save()
            self.stdout.write(self.style.SUCCESS(
                f"Rol 'Cliente' asignado con permisos: {[p.codename for p in permisos_cliente]}."
            ))
        else:
            self.stdout.write(self.style.WARNING("Rol 'Cliente' sin permisos específicos (no encontrados)."))

        # Asignar rol Admin al usuario admin
        admin_user.roles.add(rol_admin)

        self.stdout.write(self.style.SUCCESS(
            f"Usuario {admin_email} asignado al rol Administrador con permisos {[p.codename for p in permisos_admin]}."
        ))

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
            pk_str = item.get("pk")

            cliente_defaults = {
                "nombre": fields["nombre"],
                "categoria": fields["categoria"],
                "activo": fields["activo"],
            }

            if pk_str:
                try:
                    client_uuid = uuid.UUID(pk_str)
                except ValueError:
                    client_uuid = None
                if client_uuid:
                    cliente, created_client = Cliente.objects.update_or_create(
                        id_cliente=client_uuid, defaults=cliente_defaults
                    )
                else:
                    cliente, created_client = Cliente.objects.get_or_create(
                        nombre=fields["nombre"], defaults=cliente_defaults
                    )
            else:
                cliente, created_client = Cliente.objects.get_or_create(
                    nombre=fields["nombre"], defaults=cliente_defaults
                )

            if created_client:
                self.stdout.write(self.style.SUCCESS(f"Cliente creado: {cliente.nombre} ({cliente.categoria})"))
            else:
                self.stdout.write(self.style.WARNING(f"Cliente actualizado: {cliente.nombre} ({cliente.categoria})"))

            # Usuario por cliente
            client_user_email = f"{fields['nombre'].lower().replace(' ', '')}@example.com"
            client_user_password = "password123"

            client_user, created_user = User.objects.get_or_create(
                email=client_user_email,
                defaults={
                    "first_name": fields["nombre"].split(' ')[0],
                    "last_name": fields["nombre"].split(' ')[-1] if len(fields["nombre"].split(' ')) > 1 else "",
                    "is_staff": False,
                    "is_superuser": False,
                    "is_active": True,
                    "is_verified": True,
                    "verification_code": None,
                    "code_created_at": None,
                },
            )
            client_user.set_password(client_user_password)
            client_user.save()

            if cliente not in client_user.clientes.all():
                client_user.clientes.add(cliente)

            # Roles cliente
            if rol_cliente not in client_user.roles.all():
                client_user.roles.add(rol_cliente)
            if rol_cliente_dev_otp_bypass not in client_user.roles.all():
                client_user.roles.add(rol_cliente_dev_otp_bypass)

        self.stdout.write(self.style.SUCCESS("Proceso de creación de usuarios y clientes finalizado."))
