from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from roles.models import Role
from clientes.models import Cliente
from ted.models import TedPerms
from analista_panel.models import AnalistaPanelPermissions

class Command(BaseCommand):
    help = "Crea o actualiza los roles y sus permisos en el sistema."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando la configuración de roles y permisos..."))

        # --- Rol Administrador ---
        rol_admin, _ = Role.objects.get_or_create(name="Administrador", defaults={"description": "Rol de Administrador con acceso total."})

        permisos_admin_codenames = [
            "access_admin_dashboard",
            "access_cotizaciones",
            "access_monedas_section",
            "access_roles_panel",
            "delete_roles",
            "access_user_client_management",
            "access_clientes_panel",
            "access_medios_acreditacion",
            "access_pagos_section",
            "puede_operar_terminal",
            "puede_gestionar_inventario",
        ]

        permisos_admin = []
        for codename in permisos_admin_codenames:
            try:
                # Buscamos el permiso sin importar a qué app pertenezca
                perm = Permission.objects.get(codename=codename)
                permisos_admin.append(perm)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Permiso '{codename}' no encontrado. Asegúrate de que las migraciones de las apps correspondientes se hayan ejecutado."))
            except Permission.MultipleObjectsReturned:
                self.stdout.write(self.style.ERROR(f"Error: Múltiples permisos encontrados para el codename '{codename}'. Por favor, revisa tus modelos."))


        # Asignar permisos al rol Administrador
        rol_admin.permissions.set(permisos_admin)
        self.stdout.write(self.style.SUCCESS(f"Rol 'Administrador' configurado con {len(permisos_admin)} permisos."))

        # --- Rol Cliente ---
        rol_cliente, _ = Role.objects.get_or_create(name="Cliente", defaults={"description": "Rol de Cliente estándar para usuarios finales."})
        
        cliente_ct = ContentType.objects.get_for_model(Cliente)
        permisos_cliente = list(Permission.objects.filter(content_type=cliente_ct))
        if permisos_cliente:
            rol_cliente.permissions.set(permisos_cliente)
            self.stdout.write(self.style.SUCCESS(f"Rol 'Cliente' configurado con permisos para el modelo Cliente."))
        else:
            self.stdout.write(self.style.WARNING("No se encontraron permisos específicos para el modelo Cliente."))

        # --- Rol Cliente_Dev_OTP_Bypass ---
        Role.objects.get_or_create(name="Cliente_Dev_OTP_Bypass", defaults={"description": "Rol especial para clientes en desarrollo que salta el OTP."})
        self.stdout.write(self.style.SUCCESS("Rol 'Cliente_Dev_OTP_Bypass' asegurado."))


        # --- Rol Analista Cambiario ---
        rol_analista, _ = Role.objects.get_or_create(name="Analista", defaults={"description": "Rol de Analista cambiario (gestión de tasas y monitoreo)."})

        permisos_analista_codenames = [
            "access_analista_dashboard",
            "access_exchange_rates",
            "view_profits_module",
            "access_cotizaciones",
            "puede_gestionar_inventario",
        ]
        
        permisos_analista = []
        for codename in permisos_analista_codenames:
            try:
                perm = Permission.objects.get(codename=codename)
                permisos_analista.append(perm)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Permiso '{codename}' para Analista no encontrado."))

        rol_analista.permissions.set(permisos_analista)
        self.stdout.write(self.style.SUCCESS(f"Rol 'Analista' configurado con {len(permisos_analista)} permisos."))

        self.stdout.write(self.style.SUCCESS("Configuración de roles y permisos finalizada."))
