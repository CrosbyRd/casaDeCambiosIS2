from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0001_initial'),  # 🔹 ajusta según tu último archivo de migración en pagos
        ('transacciones', '0001_initial'),
    ]

    operations = []
