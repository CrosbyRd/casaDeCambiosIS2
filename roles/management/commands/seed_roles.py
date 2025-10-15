from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from roles.models import Role
from clientes.models import Cliente

class Command(BaseCommand):
    help = "Crea o actualiza los roles y sus permisos en el sistema."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando la configuración de roles y permisos..."))

        # --- Helpers ---
        def get_perms_by_codenames(codenames):
            perms = []
            for code in codenames:
                try:
                    perms.append(Permission.objects.get(codename=code))
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Permiso '{code}' no encontrado. ¿Falta migración?"))
                except Permission.MultipleObjectsReturned:
                    self.stdout.write(self.style.ERROR(f"Múltiples permisos con codename '{code}'. Revisar modelos."))
            return perms

        def get_model_perms(model, only=None, exclude=None):
            ct = ContentType.objects.get_for_model(model)
            qs = Permission.objects.filter(content_type=ct)
            if only:
                qs = qs.filter(codename__in=only)
            if exclude:
                qs = qs.exclude(codename__in=exclude)
            return list(qs)

        # === ADMINISTRADOR ===
        rol_admin, _ = Role.objects.get_or_create(
            name="Administrador",
            defaults={"description": "Rol de Administrador con acceso total."}
        )

        admin_codenames = [
            # permisos “de aplicación” (no atados a un modelo específico)
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
            "access_config_panel"
        ]
        admin_perms = get_perms_by_codenames(admin_codenames)

        # + permisos del modelo Cliente (CRUD)
        admin_perms += get_model_perms(Cliente, only=[
            "add_cliente", "change_cliente", "delete_cliente", "view_cliente"
        ])

        rol_admin.permissions.set(admin_perms)
        self.stdout.write(self.style.SUCCESS(f"Rol 'Administrador' configurado con {len(admin_perms)} permisos."))

        # === CLIENTE ===
        rol_cliente, _ = Role.objects.get_or_create(
            name="Cliente",
            defaults={"description": "Rol de Cliente estándar para usuarios finales."}
        )

        # Versión A: sin permisos sobre Cliente (ni ver el panel, ni CRUD)
        rol_cliente.permissions.set([])  # ← vaciamos cualquier permiso previo
        self.stdout.write(self.style.SUCCESS("Rol 'Cliente' configurado SIN permisos sobre el modelo Cliente."))

        # === CLIENTE_Dev_OTP_Bypass (solo existencia, sin permisos especiales) ===
        Role.objects.get_or_create(
            name="Cliente_Dev_OTP_Bypass",
            defaults={"description": "Rol especial para clientes en desarrollo que salta el OTP."}
        )
        self.stdout.write(self.style.SUCCESS("Rol 'Cliente_Dev_OTP_Bypass' asegurado."))

        # === ANALISTA ===
        rol_analista, _ = Role.objects.get_or_create(
            name="Analista",
            defaults={"description": "Rol de Analista cambiario (gestión de tasas y monitoreo)."}
        )

        analista_codenames = [
            "access_analista_dashboard",
            "access_exchange_rates",
            "view_profits_module",
            "access_cotizaciones",
            "puede_gestionar_inventario",
        ]
        analista_perms = get_perms_by_codenames(analista_codenames)

        # Analista NO debe tener permisos sobre Cliente (ni panel ni CRUD)
        rol_analista.permissions.set(analista_perms)
        self.stdout.write(self.style.SUCCESS(f"Rol 'Analista' configurado con {len(analista_perms)} permisos."))

        self.stdout.write(self.style.SUCCESS("Configuración de roles y permisos finalizada."))
