# medios_acreditacion/tests/test_views.py
from django.test import TestCase, Client
from clientes.models import Cliente
from medios_acreditacion.models import TipoMedioAcreditacion, MedioAcreditacionCliente
from usuarios.models import CustomUser

HTTP_STATUS_TEXT = {
    200: "OK – Página cargada correctamente",
    302: "Found – Redirección (normalmente éxito)",
    403: "Forbidden – Acceso denegado",
    404: "Not Found – Recurso inexistente",
    400: "Bad Request – Datos inválidos en formulario",
    500: "Internal Server Error – Error del servidor",
}


class MedioAcreditacionViewsTests(TestCase):

    def setUp(self):
        self.client = Client()  # inicializar client para requests
        # Crear usuario
        self.user = CustomUser.objects.create_user(
            email="testuser@example.com",
            password="12345",
            first_name="Test",
            last_name="User"
        )
        self.client.force_login(self.user)

        # Crear cliente
        self.cliente = Cliente.objects.create(
            nombre="Cliente Test",
            # ... otros campos obligatorios de tu modelo Cliente
        )

        # Crear tipo de medio
        self.tipo = TipoMedioAcreditacion.objects.create(
            nombre="Tarjeta de Crédito"
        )

    def test_crear_medio_cliente_ok(self):
        medio = MedioAcreditacionCliente.objects.create(
            cliente=self.cliente,
            tipo=self.tipo,
            datos={"numero": "1234567890123456"},
            predeterminado=True
        )
        self.assertEqual(
            medio.cliente,
            self.cliente,
            msg="El medio de acreditación creado debería estar asociado al cliente correcto."
        )
        self.assertEqual(
            medio.tipo,
            self.tipo,
            msg="El medio de acreditación creado debería tener el tipo correcto."
        )

        # ERROR INTENCIONAL: cambiar número a valor inválido
        # medio.datos = {"numero": "abc"}
        # with self.assertRaises(Exception):
        #     medio.full_clean()

    def test_crear_medio_cliente_invalido(self):
        medio = MedioAcreditacionCliente(
            cliente=self.cliente,
            tipo=self.tipo,
            datos={}  # vacío
        )
        with self.assertRaises(
            Exception,
            msg="Se esperaba error al crear medio de acreditación con datos vacíos."
        ):
            medio.full_clean()  # valida según clean()

        # ERROR INTENCIONAL: intentar crear predeterminado sin datos
        # medio.predeterminado = True
        # with self.assertRaises(Exception):
        #     medio.full_clean()

    def test_editar_medio_cliente_ok(self):
        medio = MedioAcreditacionCliente.objects.create(
            cliente=self.cliente,
            tipo=self.tipo,
            datos={"numero": "1234567890123456"},
            predeterminado=True
        )
        medio.alias = "Master Actualizada"
        medio.datos = {"numero": "1111222233334444"}
        medio.save()
        medio.refresh_from_db()
        self.assertEqual(
            medio.alias,
            "Master Actualizada",
            msg="El alias del medio debería actualizarse correctamente."
        )
        self.assertEqual(
            medio.datos["numero"],
            "1111222233334444",
            msg="El número del medio debería actualizarse correctamente."
        )

        # ERROR INTENCIONAL: editar número a valor inválido
        # medio.datos = {"numero": "invalid"}
        # with self.assertRaises(Exception):
        #     medio.full_clean()

    def test_eliminar_medio_cliente_ok(self):
        medio = MedioAcreditacionCliente.objects.create(
            cliente=self.cliente,
            tipo=self.tipo,
            datos={"numero": "1234567890123456"},
            predeterminado=True
        )
        pk = medio.pk
        medio.delete()
        self.assertFalse(
            MedioAcreditacionCliente.objects.filter(pk=pk).exists(),
            msg="El medio debería eliminarse correctamente de la base de datos."
        )

        # ERROR INTENCIONAL: eliminar de nuevo
        # with self.assertRaises(MedioAcreditacionCliente.DoesNotExist):
        #     MedioAcreditacionCliente.objects.get(pk=pk)

    def test_lista_medios_cliente(self):
        medio = MedioAcreditacionCliente.objects.create(
            cliente=self.cliente,
            tipo=self.tipo,
            datos={"numero": "1234567890123456"},
            predeterminado=True
        )
        medios = MedioAcreditacionCliente.objects.filter(cliente=self.cliente)
        self.assertIn(
            medio,
            medios,
            msg="El medio creado debería aparecer en la lista de medios del cliente."
        )

        # ERROR INTENCIONAL: buscar cliente inexistente
        # medios = MedioAcreditacionCliente.objects.filter(cliente_id=9999)
        # self.assertEqual(len(medios), 0, msg="No deberían encontrarse medios para un cliente inexistente.")
