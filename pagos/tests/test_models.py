from django.test import TestCase
from django.core.exceptions import ValidationError
from pagos.models import TipoMedioPago

class TipoMedioPagoModelTests(TestCase):

    def test_str_retorna_nombre(self):
        """
        Verifica que el método __str__ retorna correctamente el nombre del tipo de medio de pago.
        """
        tipo = TipoMedioPago.objects.create(
            nombre="Tarjeta de Crédito",
            comision_porcentaje=5.0,
            bonificacion_porcentaje=0.0,
            activo=True
        )
        self.assertEqual(str(tipo), "Tarjeta de Crédito")

    def test_valores_por_defecto(self):
        """
        Verifica que los campos opcionales tomen los valores por defecto al crear un registro sin especificarlos.
        """
        tipo = TipoMedioPago.objects.create(nombre="Cheque")
        self.assertEqual(tipo.comision_porcentaje, 0.0)
        self.assertEqual(tipo.bonificacion_porcentaje, 0.0)
        self.assertTrue(tipo.activo)

    def test_valores_invalidos(self):
        """
        Verifica que se lance un ValidationError si se ingresan valores fuera de rango (como comision_porcentaje negativo).
        """
        tipo = TipoMedioPago(
            nombre="Medio inválido",
            comision_porcentaje=-5.0,  # inválido por MinValueValidator
            bonificacion_porcentaje=150.0  # inválido por MaxValueValidator
        )
        with self.assertRaises(ValidationError):
            tipo.full_clean()  # full_clean() valida todos los validators

    def test_comision_bonificacion_maxima(self):
        """
        Verifica que no se permitan valores mayores a 100 para comision o bonificacion.
        """
        tipo = TipoMedioPago(
            nombre="Medio inválido 2",
            comision_porcentaje=101.0,
            bonificacion_porcentaje=50.0
        )
        with self.assertRaises(ValidationError):
            tipo.full_clean()

        tipo2 = TipoMedioPago(
            nombre="Medio inválido 3",
            comision_porcentaje=50.0,
            bonificacion_porcentaje=120.0
        )
        with self.assertRaises(ValidationError):
            tipo2.full_clean()
