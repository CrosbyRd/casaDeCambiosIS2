# roles/management/commands/seed_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from roles.models import Role
from usuarios.models import CustomUser

class Command(BaseCommand):
    help = 'Crea los roles predefinidos y les asigna permisos.'

    def handle(self, *args, **options):
        # Nombres de los roles a crear
        roles_data = [
            {'name': 'ADMINISTRADOR', 'description': 'Tiene permisos de administración total.'},
            {'name': 'CAJERO', 'description': 'Puede gestionar transacciones.'},
            {'name': 'CLIENTE', 'description': 'Usuario final sin permisos especiales.'}
        ]

        # Obtener los ContentTypes de tus modelos
        try:
            user_content_type = ContentType.objects.get_for_model(CustomUser)
            role_content_type = ContentType.objects.get_for_model(Role)
        except ContentType.DoesNotExist:
            self.stdout.write(self.style.ERROR('No se encontraron ContentTypes. Asegúrate de que las migraciones estén aplicadas.'))
            return

        # Definir los permisos que asignarás a cada rol
        admin_permissions = [
            # Permisos de usuario (ejemplo)
            'add_customuser',
            'change_customuser',
            'delete_customuser',
            'view_customuser',
            # Permisos de roles
            'add_role',
            'change_role',
            'delete_role',
            'view_role',
        ]

        cashier_permissions = [
            'view_customuser',
            # Y cualquier permiso para transacciones que definas después
        ]

        # Iterar sobre los datos y crear los roles
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(name=role_data['name'], defaults={'description': role_data['description']})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Rol "{role.name}" creado.'))
            else:
                self.stdout.write(self.style.WARNING(f'Rol "{role.name}" ya existe.'))
            
            # Asignar permisos según el rol
            if role.name == 'ADMINISTRADOR':
                permissions_to_assign = admin_permissions
            elif role.name == 'CAJERO':
                permissions_to_assign = cashier_permissions
            else:
                permissions_to_assign = []

            for perm_codename in permissions_to_assign:
                try:
                    # Usar el ContentType del modelo que corresponde
                    if 'customuser' in perm_codename:
                        permission = Permission.objects.get(codename=perm_codename, content_type=user_content_type)
                    elif 'role' in perm_codename:
                        permission = Permission.objects.get(codename=perm_codename, content_type=role_content_type)
                    else:
                        continue
                    
                    role.permissions.add(permission)
                    self.stdout.write(self.style.SUCCESS(f'Permiso "{perm_codename}" asignado al rol "{role.name}".'))
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Permiso "{perm_codename}" no existe.'))

        self.stdout.write(self.style.SUCCESS('Proceso de inicialización de roles completado.'))