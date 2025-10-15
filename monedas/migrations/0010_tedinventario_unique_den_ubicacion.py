# monedas/migrations/0010_tedinventario_unique_den_ubicacion.py
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("monedas", "0009_tedinventario_add_ubicacion_and_fk"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="tedinventario",
            constraint=models.UniqueConstraint(
                fields=["denominacion", "ubicacion"],
                name="uniq_tedinventario_den_ubicacion",
            ),
        ),
    ]
