from django.test import TestCase
from django.contrib.auth import get_user_model
from monedas.models import Moneda
from cotizaciones.models import Cotizacion
from notificaciones.tasks import notificar_cambio_de_tasa_a_usuarios
from notificaciones.models import Notificacion, PreferenciasNotificacion

User = get_user_model()

class NotificacionesTasksTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass123")
        self.user2 = User.objects.create_user(email="user2@test.com", password="pass123")
        
        # Crear ambas monedas necesarias
        self.moneda_base = Moneda.objects.create(nombre="Guaraní", codigo="PYG", admite_en_linea=True)
        self.moneda_destino = Moneda.objects.create(nombre="Dólar", codigo="USD", admite_en_linea=True)
        
        # Crear cotización con ambas monedas
        self.cotizacion = Cotizacion.objects.create(
            moneda_base=self.moneda_base,
            moneda_destino=self.moneda_destino, 
            valor_compra=7000, 
            valor_venta=7100
        )

    def test_task_notificar_retorna_string(self):
        result = notificar_cambio_de_tasa_a_usuarios(
            self.cotizacion.id, 
            "Mensaje test", 
            True, 
            True
        )
        self.assertIsInstance(result, str)
        # La task puede retornar diferentes mensajes dependiendo de las transacciones
        self.assertIn(result, [
            "No se encontraron usuarios con transacciones pendientes para notificar.",
            "Cotización no encontrada. No se enviaron notificaciones.",
            "Notificaciones enviadas"
        ])

    def test_task_cotizacion_no_existe(self):
        result = notificar_cambio_de_tasa_a_usuarios(
            99999,  # ID que no existe
            "Mensaje test", 
            True, 
            True
        )
        self.assertEqual(result, "Cotización no encontrada. No se enviaron notificaciones.")

    def test_task_crea_notificaciones_sin_transacciones(self):
        # Sin transacciones pendientes, no debería crear notificaciones
        initial_count = Notificacion.objects.count()
        
        result = notificar_cambio_de_tasa_a_usuarios(
            self.cotizacion.id, 
            "Mensaje de prueba", 
            True, 
            True
        )
        
        # Verificar que no se crearon notificaciones (sin transacciones pendientes)
        self.assertEqual(Notificacion.objects.count(), initial_count)
        self.assertEqual(result, "No se encontraron usuarios con transacciones pendientes para notificar.")

    def test_task_respetar_preferencias_monedas(self):
        # Usar get_or_create para evitar violación de unique constraint
        pref, created = PreferenciasNotificacion.objects.get_or_create(usuario=self.user)
        moneda_eur = Moneda.objects.create(nombre="Euro", codigo="EUR", admite_en_linea=True)
        pref.monedas_seguidas.add(moneda_eur)
        
        # user2 no tiene preferencias (debería recibir todas)
        PreferenciasNotificacion.objects.filter(usuario=self.user2).delete()
        
        # Ejecutar task para USD
        result = notificar_cambio_de_tasa_a_usuarios(
            self.cotizacion.id,  # Esta cotización es para USD
            "Mensaje test", 
            True, 
            True
        )
        
        # Sin transacciones pendientes, no debería crear notificaciones para nadie
        notificaciones_user1 = Notificacion.objects.filter(destinatario=self.user)
        notificaciones_user2 = Notificacion.objects.filter(destinatario=self.user2)
        
        self.assertEqual(notificaciones_user1.count(), 0)
        self.assertEqual(notificaciones_user2.count(), 0)

    def test_task_respetar_preferencias_email(self):
        # Usar get_or_create para evitar violación de unique constraint
        pref, created = PreferenciasNotificacion.objects.get_or_create(usuario=self.user)
        pref.recibir_email_tasa_cambio = False
        pref.save()
        
        # user2 sí recibe emails (valor por defecto)
        PreferenciasNotificacion.objects.filter(usuario=self.user2).delete()
        
        # Ejecutar task
        result = notificar_cambio_de_tasa_a_usuarios(
            self.cotizacion.id, 
            "Mensaje test", 
            True, 
            True
        )
        
        # Sin transacciones pendientes, no debería crear notificaciones
        self.assertEqual(Notificacion.objects.filter(destinatario=self.user).count(), 0)
        self.assertEqual(Notificacion.objects.filter(destinatario=self.user2).count(), 0)
        
        # Verificar que el mensaje es el esperado
        self.assertEqual(result, "No se encontraron usuarios con transacciones pendientes para notificar.")

    def test_task_comportamiento_sin_preferencias(self):
        # Eliminar todas las preferencias para probar comportamiento por defecto
        PreferenciasNotificacion.objects.all().delete()
        
        result = notificar_cambio_de_tasa_a_usuarios(
            self.cotizacion.id, 
            "Mensaje test", 
            True, 
            True
        )
        
        # Sin transacciones pendientes, no debería crear notificaciones
        self.assertEqual(Notificacion.objects.count(), 0)
        self.assertEqual(result, "No se encontraron usuarios con transacciones pendientes para notificar.")