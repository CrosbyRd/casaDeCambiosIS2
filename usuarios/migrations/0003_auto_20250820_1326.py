# usuarios/migrations/0003_populate_roles.py (El nombre puede variar, solo asegúrate de que sea el archivo correcto)

from django.db import migrations

def populate_roles(apps, schema_editor):
    # Importa los modelos en su estado de la migración
    CustomUser = apps.get_model('usuarios', 'CustomUser')
    Role = apps.get_model('roles', 'Role')

    # Crea los roles si no existen
    admin_role, _ = Role.objects.get_or_create(name='ADMINISTRADOR')
    cajero_role, _ = Role.objects.get_or_create(name='CAJERO')
    cliente_role, _ = Role.objects.get_or_create(name='CLIENTE')

    # Asigna los roles a los usuarios existentes
    for user in CustomUser.objects.all():
        if user.tipo_usuario == 'ADMIN':
            user.roles.add(admin_role)
        elif user.tipo_usuario == 'CAJERO':
            user.roles.add(cajero_role)
        elif user.tipo_usuario == 'CLIENTE':
            user.roles.add(cliente_role)

class Migration(migrations.Migration):

    dependencies = [
        # La dependencia a la migración que añadió el campo `roles`.
        ('usuarios', '0002_customuser_roles'),
        # La dependencia a la migración inicial de la app de roles.
        ('roles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_roles),
    ]
