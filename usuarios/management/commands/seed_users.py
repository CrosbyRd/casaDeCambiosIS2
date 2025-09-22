import json
import uuid # Importar el módulo uuid
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from roles.models import Role
from clientes.models import Cliente # Importar el modelo Cliente

class Command(BaseCommand):
    help = "Crea/actualiza usuarios Administradores y Clientes con roles y permisos."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        self.stdout.write(self.style.SUCCESS("Iniciando creación de usuarios Administradores y Clientes..."))

        # --- Crear usuario admin de la app ---
        admin_email = "globalexchangea2@gmail.com"
        admin_password = "password123"
        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "first_name": "Admin",
                "last_name": "Principal",
                "is_staff": True,     # puede loguearse como staff
                "is_superuser": True, # Es superusuario global para bypass de OTP en desarrollo
                "is_active": True,
                "is_verified": True,
                "verification_code": None, # Deshabilitar OTP para admin
                "code_created_at": None,   # Deshabilitar OTP para admin
            },
        )

        if created:
            admin_user.set_password(admin_password)
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Usuario Administrador creado: {admin_email}"))
        else:
            self.stdout.write(self.style.WARNING(f"Usuario Administrador ya existía: {admin_email}"))

        # --- Usar update_or_create para simplificar y asegurar la actualización del admin
        defaults = {
            "first_name": admin_user.first_name,
            "last_name": admin_user.last_name,
            "is_staff": True,     # Asegurar que sea staff
            "is_superuser": True, # Asegurar que sea superusuario para bypass de OTP
            "is_active": admin_user.is_active,
            "is_verified": admin_user.is_verified,
            "verification_code": None, # Deshabilitar OTP para admin
            "code_created_at": None,   # Deshabilitar OTP para admin
        }

        admin_user, created = User.objects.update_or_create(
            email=admin_email,
            defaults=defaults
        )

        # Siempre establecer/actualizar la contraseña del admin
        if admin_password:
            admin_user.set_password(admin_password)
            admin_user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"Creado y contraseña establecida para Administrador: {admin_email}"))
        else:
            self.stdout.write(self.style.WARNING(f"Actualizado y contraseña re-establecida para Administrador: {admin_email}"))

        # --- Crear Rol Administrador ---
        rol_admin, _ = Role.objects.get_or_create(
            name="Administrador",
            defaults={"description": "Rol de Administrador"}
        )

        # --- Buscar permisos personalizados para Administrador ---
        permisos_admin_codenames = [
                "access_admin_dashboard",   # Panel Admin
                "access_cotizaciones",      # Cotizaciones
                "access_monedas_section",   # Monedas
                "access_roles_panel",       # NUEVO: acceso a Roles
                "delete_roles",             # NUEVO: eliminar Roles
                "access_user_client_management",  # NUEVO:  acceso a asociacion cliente a usuario
                "access_clientes_panel",   #accede al menu de administracion de clientes
            ]

        permisos_admin = []
        for codename in permisos_admin_codenames:
            try:
                perm = Permission.objects.get(codename=codename)
                permisos_admin.append(perm)
            except Permission.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"El permiso '{codename}' no existe. "
                    f"Ejecuta 'makemigrations' y 'migrate' en la app correspondiente primero."
                ))

        # Asignar permisos al rol Administrador
        if permisos_admin:
            rol_admin.permissions.set(permisos_admin) # Usar set para reemplazar todos los permisos existentes
            rol_admin.save()

        # Asignar rol Administrador al usuario admin
        admin_user.roles.add(rol_admin)

        self.stdout.write(self.style.SUCCESS(
            f"Usuario {admin_email} asignado al rol Administrador con permisos {[p.codename for p in permisos_admin]}."
        ))

        # --- Crear Rol Cliente ---
        rol_cliente, _ = Role.objects.get_or_create(
            name="Cliente",
            defaults={"description": "Rol de Cliente estándar para usuarios finales."}
        )

        # --- Crear Rol Cliente para bypass de OTP en desarrollo ---
        rol_cliente_dev_otp_bypass, _ = Role.objects.get_or_create(
            name="Cliente_Dev_OTP_Bypass",
            defaults={"description": "Rol especial para clientes en desarrollo que salta el OTP."}
        )

        # --- Buscar permisos genéricos para el modelo Cliente ---
        cliente_content_type = ContentType.objects.get_for_model(Cliente)
        permisos_cliente_genericos = Permission.objects.filter(content_type=cliente_content_type)
        
        permisos_cliente = []
        for perm in permisos_cliente_genericos:
            permisos_cliente.append(perm)
            self.stdout.write(self.style.WARNING(f"Permiso genérico para Cliente encontrado: '{perm.codename}'"))
        
        # Asignar permisos al rol Cliente
        if permisos_cliente:
            rol_cliente.permissions.set(permisos_cliente) # Usar set para reemplazar todos los permisos existentes
            rol_cliente.save()
            self.stdout.write(self.style.SUCCESS(
                f"Rol 'Cliente' asignado con permisos genéricos: {[p.codename for p in permisos_cliente]}."
            ))
        else:
            self.stdout.write(self.style.WARNING("No se encontraron permisos genéricos para el modelo Cliente. El rol 'Cliente' se creó sin permisos específicos."))


        # --- Cargar clientes desde el fixture y crear usuarios asociados ---
        # La ruta debe ser relativa a la raíz del proyecto, no a la app 'usuarios'.
        # Path(__file__).resolve().parent.parent.parent apunta a la carpeta 'usuarios'.
        # Necesitamos ir un nivel más arriba para llegar a la raíz del proyecto.
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        fixture_path = project_root / "clientes" / "fixtures" / "clientes.json"
        
        if not fixture_path.exists():
            self.stdout.write(self.style.ERROR(f"Fixture de clientes no encontrado en: {fixture_path}"))
            return

        with open(fixture_path, 'r', encoding='utf-8') as f:
            clientes_data = json.load(f)

        for item in clientes_data:
            if item["model"] == "clientes.cliente":
                client_fields = item["fields"]
                client_pk_str = item.get("pk") # Obtener 'pk' si existe

                cliente_defaults = {
                    "nombre": client_fields["nombre"],
                    "categoria": client_fields["categoria"],
                    "activo": client_fields["activo"],
                    # No incluir fecha_registro y ultima_modificacion si auto_now_add/auto_now
                    # se encargan de ello, o si se quieren valores específicos, incluirlos.
                }

                if client_pk_str:
                    # Si 'pk' está presente, intentar usarlo
                    try:
                        client_uuid = uuid.UUID(client_pk_str)
                    except ValueError as e:
                        self.stdout.write(self.style.ERROR(f"Error al convertir UUID '{client_pk_str}' (repr: {repr(client_pk_str)}): {e}. Se generará un nuevo UUID."))
                        client_uuid = None # Forzar la creación de un nuevo UUID
                    
                    if client_uuid:
                        # Crear o actualizar el cliente con el UUID proporcionado
                        cliente, created_client = Cliente.objects.update_or_create(
                            id_cliente=client_uuid,
                            defaults=cliente_defaults
                        )
                    else:
                        # Crear un nuevo cliente si el UUID proporcionado era inválido
                        cliente, created_client = Cliente.objects.get_or_create(
                            nombre=client_fields["nombre"], # Usar nombre para get_or_create si no hay pk
                            defaults=cliente_defaults
                        )
                else:
                    # Si 'pk' no está presente, crear un nuevo cliente (Django generará el UUID)
                    cliente, created_client = Cliente.objects.get_or_create(
                        nombre=client_fields["nombre"], # Usar nombre para get_or_create si no hay pk
                        defaults=cliente_defaults
                    )
                
                if created_client:
                    self.stdout.write(self.style.SUCCESS(f"Cliente creado: {cliente.nombre} ({cliente.categoria})"))
                else:
                    self.stdout.write(self.style.WARNING(f"Cliente actualizado: {cliente.nombre} ({cliente.categoria})"))

                # Crear usuario para el cliente
                client_user_email = f"{client_fields['nombre'].lower().replace(' ', '')}@example.com"
                client_user_password = "password123"
                
                client_user, created_user = User.objects.get_or_create(
                    email=client_user_email,
                    defaults={
                        "first_name": client_fields["nombre"].split(' ')[0],
                        "last_name": client_fields["nombre"].split(' ')[-1] if len(client_fields["nombre"].split(' ')) > 1 else "",
                        "is_staff": False,
                        "is_superuser": False,
                        "is_active": True,
                        "is_verified": True,
                        "verification_code": None, # Deshabilitar OTP para clientes
                        "code_created_at": None,   # Deshabilitar OTP para clientes
                    },
                )

                if created_user:
                    client_user.set_password(client_user_password)
                    client_user.save()
                    self.stdout.write(self.style.SUCCESS(f"Usuario cliente creado: {client_user_email}"))
                else:
                    self.stdout.write(self.style.WARNING(f"Usuario cliente ya existía: {client_user_email}"))
                
                # Asegurar que la contraseña esté establecida
                client_user.set_password(client_user_password)
                client_user.save()

                # Asociar cliente con usuario (ManyToMany)
                if not cliente in client_user.clientes.all():
                    client_user.clientes.add(cliente)
                    self.stdout.write(self.style.SUCCESS(f"Cliente '{cliente.nombre}' asociado a usuario '{client_user_email}'."))
                else:
                    self.stdout.write(self.style.WARNING(f"Cliente '{cliente.nombre}' ya estaba asociado a usuario '{client_user_email}'."))

                # Asignar rol Cliente estándar al usuario
                if not rol_cliente in client_user.roles.all():
                    client_user.roles.add(rol_cliente)
                    self.stdout.write(self.style.SUCCESS(f"Rol 'Cliente' asignado a usuario '{client_user_email}'."))
                else:
                    self.stdout.write(self.style.WARNING(f"Rol 'Cliente' ya estaba asignado a usuario '{client_user_email}'."))
                
                # Asignar rol de bypass de OTP en desarrollo al usuario
                if not rol_cliente_dev_otp_bypass in client_user.roles.all():
                    client_user.roles.add(rol_cliente_dev_otp_bypass)
                    self.stdout.write(self.style.SUCCESS(f"Rol 'Cliente_Dev_OTP_Bypass' asignado a usuario '{client_user_email}'."))
                else:
                    self.stdout.write(self.style.WARNING(f"Rol 'Cliente_Dev_OTP_Bypass' ya estaba asignado a usuario '{client_user_email}'."))

        self.stdout.write(self.style.SUCCESS("Proceso de creación de usuarios y clientes finalizado."))
