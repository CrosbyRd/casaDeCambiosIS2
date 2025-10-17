from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0001_initial'),  # 🔹 ajusta según tu último archivo de migración en pagos
        ('transacciones', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaccion',
            name='medio_pago_utilizado',
            field=models.ForeignKey(
                to='pagos.tipomediopago',
                on_delete=django.db.models.deletion.PROTECT,
                null=True,
                blank=True,
                help_text='Medio de pago utilizado por el cliente para pagar (solo en VENTA de divisa).',
            ),
        ),
    ]
