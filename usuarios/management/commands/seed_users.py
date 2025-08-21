from django.core.management.base import BaseCommand
from usuarios.models import CustomUser

class Command(BaseCommand):
    help = 'Crea usuarios iniciales para la base de datos'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando la creación de usuarios iniciales...'))

        # Lista de usuarios a crear
        users_to_create = [
            {
                'username': 'admin_general',
                'email': 'admin@casadecambio.com',
                'password': 'password123',
                'first_name': 'Admin',
                'last_name': 'Principal',
                'tipo_usuario': CustomUser.UserTypes.ADMIN
            },
            {
                'username': 'analista_uno',
                'email': 'analista1@casadecambio.com',
                'password': 'password123',
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'tipo_usuario': CustomUser.UserTypes.ANALISTA
            },
            {
                'username': 'cliente_test',
                'email': 'cliente@example.com',
                'password': 'password123',
                'first_name': 'Ana',
                'last_name': 'García',
                'tipo_usuario': CustomUser.UserTypes.CLIENTE
            },
                        {
                'username': 'beta_tester',
                'email': 'lclc@mgail.com',
                'password': 'ttu789',
                'first_name': 'Lope',
                'last_name': 'GGG',
                'tipo_usuario': CustomUser.UserTypes.CLIENTE
            }
        ]

        for user_data in users_to_create:
            # Revisa si el usuario ya existe antes de crearlo
            if not CustomUser.objects.filter(username=user_data['username']).exists():
                CustomUser.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    tipo_usuario=user_data['tipo_usuario']
                )
                self.stdout.write(self.style.SUCCESS(f"Usuario '{user_data['username']}' creado exitosamente."))
            else:
                self.stdout.write(self.style.WARNING(f"Usuario '{user_data['username']}' ya existe. Saltando."))
        
        self.stdout.write(self.style.SUCCESS('Proceso de seeding finalizado.'))