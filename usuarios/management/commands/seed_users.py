from django.core.management.base import BaseCommand
from usuarios.models import CustomUser
from roles.models import Role  # Importa el modelo Role

class Command(BaseCommand):
    help = 'Crea usuarios y asigna roles iniciales para la base de datos'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando la creación de usuarios y roles iniciales...'))

        # Asegura que los roles existan. Si ya existen, los recupera.
        admin_role, _ = Role.objects.get_or_create(name='admin')
        cajero_role, _ = Role.objects.get_or_create(name='cajero')
        cliente_role, _ = Role.objects.get_or_create(name='cliente')

        # Diccionario para mapear nombres de roles a objetos de rol
        role_map = {
            'admin': admin_role,
            'cajero': cajero_role,
            'cliente': cliente_role
        }

        users_to_create = [
            {
                'username': 'admin_general',
                'email': 'admin@casadecambio.com',
                'password': 'password123',
                'first_name': 'Admin',
                'last_name': 'Principal',
                'role_name': 'admin' # Nuevo campo para el nombre del rol
            },
            {
                'username': 'cajero_uno',
                'email': 'cajero1@casadecambio.com',
                'password': 'password123',
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'role_name': 'cajero'
            },
            {
                'username': 'cliente_test',
                'email': 'cliente@example.com',
                'password': 'password123',
                'first_name': 'Ana',
                'last_name': 'García',
                'role_name': 'cliente'
            },
            {
                'username': 'cliente_test2',
                'email': 'cliente222@example.com',
                'password': 'password123',
                'first_name': 'Ana',
                'last_name': 'García',
                'role_name': 'cliente'
            }
        ]

        for user_data in users_to_create:
            username = user_data['username']
            role_name = user_data['role_name']

            # Revisa si el usuario ya existe para evitar duplicados
            if not CustomUser.objects.filter(username=username).exists():
                # Crea el usuario. Nota: ya no se usa 'tipo_usuario' aquí.
                user = CustomUser.objects.create_user(
                    username=username,
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name']
                )

                # Asigna el rol al usuario usando el método 'add' del ManyToManyField
                user.roles.add(role_map[role_name])
                
                self.stdout.write(self.style.SUCCESS(f"Usuario '{username}' creado exitosamente y rol '{role_name}' asignado."))
            else:
                self.stdout.write(self.style.WARNING(f"Usuario '{username}' ya existe. Saltando."))
        
        self.stdout.write(self.style.SUCCESS('Proceso de seeding finalizado.'))