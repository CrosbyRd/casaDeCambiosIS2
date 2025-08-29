""" # usuarios/management/commands/seed_users.py
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
                self.stdout.write(self.style.WARNING(f'El usuario "{email}" ya existe, saltando su creación.')) """

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea usuarios iniciales para la base de datos'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Iniciando la creación de usuarios iniciales...'))

        # Usamos el identificador real del modelo (normalmente 'email')
        key_field = User.USERNAME_FIELD  # p.ej. 'email'

        # Lista de usuarios a crear —> usa email como clave
        users_to_create = [
            {
                'email': 'admin@casadecambio.com',
                'password': 'password123',
                'first_name': 'Admin',
                'last_name': 'Principal',
                'role': 'ADMIN',
            },
            {
                'email': 'analista1@casadecambio.com',
                'password': 'password123',
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'role': 'ANALISTA',
            },
            {
                'email': 'cliente@example.com',
                'password': 'password123',
                'first_name': 'Ana',
                'last_name': 'García',
                'role': 'CLIENTE',
            },
            {
                'email': 'lclc@mgail.com',
                'password': 'ttu789',
                'first_name': 'Lope',
                'last_name': 'GGG',
                'role': 'CLIENTE',
            },
        ]

        # Utilidad para saber si el modelo tiene un campo con ese nombre
        model_field_names = {f.name for f in User._meta.get_fields()}
        has_tipo_usuario = 'tipo_usuario' in model_field_names

        created = 0
        skipped = 0

        with transaction.atomic():
            for data in users_to_create:
                key_value = data.get(key_field)
                if not key_value:
                    self.stdout.write(self.style.ERROR(
                        f"Falta el campo clave '{key_field}' en: {data}"
                    ))
                    continue

                # ¿Ya existe?
                if User.objects.filter(**{key_field: key_value}).exists():
                    self.stdout.write(self.style.WARNING(
                        f"Usuario '{key_value}' ya existe. Saltando."
                    ))
                    skipped += 1
                    continue

                # Flags por rol
                role = data.get('role', '').upper()
                is_staff = role in ('ADMIN', 'ANALISTA')
                is_superuser = role == 'ADMIN'

                # Campos extra (no incluir password ni role)
                extra = {
                    'first_name': data.get('first_name', ''),
                    'last_name': data.get('last_name', ''),
                    'is_staff': is_staff,
                    'is_superuser': is_superuser,
                    'is_active': True,
                }

                # Crear con el manager para que hashee la password
                user = User.objects.create_user(
                    password=data['password'],
                    **{key_field: key_value},
                    **extra
                )

                # Si tu modelo realmente tiene 'tipo_usuario', lo fijamos
                if has_tipo_usuario:
                    # Si definiste TextChoices en User.UserTypes, intentamos mapear
                    if hasattr(User, 'UserTypes'):
                        try:
                            # p.ej. User.UserTypes.ADMIN
                            value = getattr(User.UserTypes, role)
                        except AttributeError:
                            value = role  # usa el texto si no coincide
                        setattr(user, 'tipo_usuario', value)
                    else:
                        setattr(user, 'tipo_usuario', role)
                    user.save(update_fields=['tipo_usuario'])

                self.stdout.write(self.style.SUCCESS(f"Usuario '{key_value}' creado exitosamente."))
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Proceso de seeding finalizado. Creados: {created} | Ya existían: {skipped}'
        ))
