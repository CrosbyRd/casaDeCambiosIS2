# monedas/migrations/0009_tedinventario_add_ubicacion_and_fk.py
from django.db import migrations, models
import django.db.models.deletion

DEFAULT_UBICACION = "Campus, San Lorenzo – Paraguay"

def fill_ubicacion(apps, schema_editor):
    TedInventario = apps.get_model("monedas", "TedInventario")
    for inv in TedInventario.objects.all():
        if not getattr(inv, "ubicacion", None):
            inv.ubicacion = DEFAULT_UBICACION
            inv.save(update_fields=["ubicacion"])

class Migration(migrations.Migration):

    dependencies = [
        ("monedas", "0008_teddenominacion_tedinventario_tedmovimiento"),
    ]

    operations = [
        # 1) Cambia OneToOne -> ForeignKey (elimina la unicidad previa por 'denominacion')
        migrations.AlterField(
            model_name="tedinventario",
            name="denominacion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="stock",
                to="monedas.teddenominacion",
                help_text="Denominación cuyo stock se registra.",
            ),
        ),
        # 2) Agrega 'ubicacion'
        migrations.AddField(
            model_name="tedinventario",
            name="ubicacion",
            field=models.CharField(
                max_length=180,
                default=DEFAULT_UBICACION,
                help_text="Ubicación física/lógica del TED (ej.: 'Campus, San Lorenzo – Paraguay').",
            ),
            preserve_default=False,
        ),
        # 3) Rellena valor por defecto para registros existentes (por seguridad)
        migrations.RunPython(fill_ubicacion, migrations.RunPython.noop),
        # 4) Índice por ubicación (útil para reportes/filtros)
        migrations.AddIndex(
            model_name="tedinventario",
            index=models.Index(fields=["ubicacion"], name="idx_tedinv_ubicacion"),
        ),
    ]
