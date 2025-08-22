# usuarios/management/commands/seed_users.py
from django.core.management.base import BaseCommand
from usuarios.models import CustomUser
from roles.models import Role
from django.utils import timezone

class Command(BaseCommand):
    help = 'Crea los usuarios iniciales para el sistema.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando la creación de usuarios iniciales...'))

        users_to_create = [
            {'email': 'admin@example.com', 'password': 'password123', 'first_name': 'Admin', 'last_name': 'General', 'role': 'ADMINISTRADOR'},
            {'email': 'cajero@example.com', 'password': 'password123', 'first_name': 'Cajero', 'last_name': 'Uno', 'role': 'CAJERO'},
            {'email': 'cliente@example.com', 'password': 'password123', 'first_name': 'Cliente', 'last_name': 'Prueba', 'role': 'CLIENTE'},
        ]

        for user_data in users_to_create:
            email = user_data['email']
            role_name = user_data.pop('role')

            if not CustomUser.objects.filter(email=email).exists():
                try:
                    role = Role.objects.get(name=role_name)
                    user = CustomUser.objects.create_user(
                        email=user_data['email'],
                        password=user_data['password'],
                        first_name=user_data.get('first_name', ''),
                        last_name=user_data.get('last_name', ''),
                        is_staff=role.name == 'ADMINISTRADOR',
                        is_superuser=role.name == 'ADMINISTRADOR'
                    )
                    user.roles.add(role)
                    self.stdout.write(self.style.SUCCESS(f'Usuario "{email}" creado con éxito.'))
                except Role.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Error: El rol "{role_name}" no existe.'))
                    return
            else:
                self.stdout.write(self.style.WARNING(f'El usuario "{email}" ya existe, saltando su creación.'))