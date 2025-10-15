from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from roles.models import Role
from clientes.models import Cliente
from configuracion.models import TransactionLimit  # para CRUD de límites

class Command(BaseCommand):
    help = "Crea/actualiza roles y permisos."

    def _get_perms(self, *, codenames=None, model=None, only=None):
        if codenames:
            return list(Permission.objects.filter(codename__in=codenames))
        if model:
            ct = ContentType.objects.get_for_model(model)
            qs = Permission.objects.filter(content_type=ct)
            if only:
                qs = qs.filter(codename__in=only)
            return list(qs)
        return []

    @transaction.atomic
    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS("Configurando roles…"))

        # === ADMINISTRADOR ===
        admin, _ = Role.objects.get_or_create(name="Administrador",
                                              defaults={"description": "Acceso total."})

        admin_custom = self._get_perms(codenames=[
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
            "access_config_panel",  # permiso custom en configuracion
        ])
        admin_clientes_crud = self._get_perms(model=Cliente, only=[
            "add_cliente","change_cliente","delete_cliente","view_cliente"
        ])
        admin_limits_crud = self._get_perms(model=TransactionLimit, only=[
            "add_transactionlimit","change_transactionlimit",
            "delete_transactionlimit","view_transactionlimit"
        ])

        admin.permissions.set(admin_custom + admin_clientes_crud + admin_limits_crud)

        # === CLIENTE ===
        cliente, _ = Role.objects.get_or_create(name="Cliente",
                                                defaults={"description": "Usuario final cliente."})

        # PRINCIPIO DE MÍNIMO PRIVILEGIO:
        # Solo ver su entidad Cliente si tu UI lo necesita (view_cliente),
        # NO add/change/delete, NO access_clientes_panel, NO access_config_panel.
        cliente_perms = self._get_perms(model=Cliente, only=["view_cliente"])

        # Si tu flujo de transacciones exige un permiso para habilitar la validación/confirmación,
        # agrégalo explícitamente acá (por ejemplo, "access_pagos_section" o uno propio de tu app de pagos).
        # EJEMPLO (descomentar/ajustar si corresponde):
        # cliente_perms += self._get_perms(codenames=["access_pagos_section"])  # ← AJUSTAR si tu flujo lo exige

        cliente.permissions.set(cliente_perms)

        # === ANALISTA ===
        analista, _ = Role.objects.get_or_create(name="Analista",
                                                defaults={"description": "Analista cambiario."})
        analista_perms = self._get_perms(codenames=[
            "access_analista_dashboard",
            "access_exchange_rates",
            "view_profits_module",
            "access_cotizaciones",
            "puede_gestionar_inventario",
        ])
        # Analista NO debe tocar clientes ni configuración
        analista.permissions.set(analista_perms)

        self.stdout.write(self.style.SUCCESS("Roles configurados."))
