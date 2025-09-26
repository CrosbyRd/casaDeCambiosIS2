from django.test import TestCase
from medios_acreditacion.models import TipoMedioAcreditacion, CampoMedioAcreditacion, MedioAcreditacionCliente
from clientes.models import Cliente
from decimal import Decimal

class MedioAcreditacionModelTests(TestCase):

    def setUp(self):
        # Crear cliente sin usuario (modelo actualizado)
        self.cliente = Cliente.objects.create(nombre="Cliente Test")

        # Crear tipo y campos
        self.tipo = TipoMedioAcreditacion.objects.create(nombre="Tarjeta Crédito")
        self.campo = CampoMedioAcreditacion.objects.create(
            tipo_medio=self.tipo,
            nombre="numero_tarjeta",
            tipo_dato=CampoMedioAcreditacion.TipoDato.NUMERO,
            obligatorio=True
        )

    def test_str_modelo_medio(self):
        """Verifica que el __str__ de MedioAcreditacionCliente sea 'Tipo - Cliente'"""
        medio = MedioAcreditacionCliente.objects.create(
            cliente=self.cliente,
            tipo=self.tipo,
            alias="Visa 1234",
            datos={"numero_tarjeta": "1234567890123456"},
            activo=True
        )
        self.assertEqual(
            str(medio),
            "Tarjeta Crédito - Cliente Test",
            msg="El __str__ debería mostrar correctamente 'Tipo - Cliente'."
        )

    def test_predeterminado_desactiva_otros(self):
        """Al marcar un medio como predeterminado, los anteriores se desmarcan"""
        medio1 = MedioAcreditacionCliente.objects.create(
            cliente=self.cliente,
            tipo=self.tipo,
            alias="M1",
            datos={"numero_tarjeta": "1111"},
            predeterminado=True
        )
        medio2 = MedioAcreditacionCliente.objects.create(
            cliente=self.cliente,
            tipo=self.tipo,
            alias="M2",
            datos={"numero_tarjeta": "2222"},
            predeterminado=True
        )
        medio1.refresh_from_db()
        self.assertFalse(
            medio1.predeterminado,
            msg="Al marcar un nuevo medio como predeterminado, los anteriores deben desmarcarse."
        )
