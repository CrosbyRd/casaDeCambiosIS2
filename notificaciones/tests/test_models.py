from django.test import TestCase
from django.contrib.auth import get_user_model
from monedas.models import Moneda
from notificaciones.models import PreferenciasNotificacion, Notificacion
import uuid

User = get_user_model()

class NotificacionesModelsTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass123")
        self.moneda = Moneda.objects.create(nombre="Dólar", codigo="USD", admite_en_linea=True)
        self.moneda2 = Moneda.objects.create(nombre="Euro", codigo="EUR", admite_en_linea=True)

    def test_preferencias_creacion(self):
        PreferenciasNotificacion.objects.filter(usuario=self.user).delete()
        pref = PreferenciasNotificacion.objects.create(usuario=self.user)
        self.assertEqual(str(pref), f"Preferencias de {self.user.email}")
        self.assertTrue(pref.recibir_email_tasa_cambio)  # Valor por defecto

    def test_preferencias_monedas_seguidas(self):
        PreferenciasNotificacion.objects.filter(usuario=self.user).delete()
        pref = PreferenciasNotificacion.objects.create(usuario=self.user)
        pref.monedas_seguidas.add(self.moneda, self.moneda2)
        self.assertEqual(pref.monedas_seguidas.count(), 2)
        self.assertIn(self.moneda, pref.monedas_seguidas.all())
        self.assertIn(self.moneda2, pref.monedas_seguidas.all())

    def test_preferencias_relacion_usuario(self):
        PreferenciasNotificacion.objects.filter(usuario=self.user).delete()
        pref = PreferenciasNotificacion.objects.create(usuario=self.user)
        self.assertEqual(pref.usuario, self.user)
        self.assertEqual(self.user.preferencias_notificacion, pref)

    def test_notificacion_creacion(self):
        noti = Notificacion.objects.create(
            destinatario=self.user, 
            mensaje="Mensaje de prueba"  # Mensaje más corto
        )
        expected_str = f"Notificación para {self.user.email}: Mensaje de prueba..."
        self.assertEqual(str(noti), expected_str)
        self.assertFalse(noti.leida)
        self.assertFalse(noti.silenciada)
        self.assertIsNotNone(noti.fecha_creacion)

    def test_notificacion_uuid_primary_key(self):
        noti = Notificacion.objects.create(destinatario=self.user, mensaje="Test UUID")
        self.assertIsInstance(noti.id, uuid.UUID)

    def test_notificacion_url_destino_opcional(self):
        noti = Notificacion.objects.create(
            destinatario=self.user, 
            mensaje="Notificación con URL",
            url_destino="https://ejemplo.com"
        )
        self.assertEqual(noti.url_destino, "https://ejemplo.com")

    def test_notificacion_ordering(self):
        # Crear notificaciones (se crean con fechas diferentes automáticamente)
        noti1 = Notificacion.objects.create(
            destinatario=self.user, 
            mensaje="Notificación 1"
        )
        noti2 = Notificacion.objects.create(
            destinatario=self.user, 
            mensaje="Notificación 2"
        )
        
        # Verificar que la más reciente aparece primero
        notificaciones = Notificacion.objects.all()
        self.assertEqual(notificaciones[0], noti2)
        self.assertEqual(notificaciones[1], noti1)

    def test_notificacion_estados(self):
        noti = Notificacion.objects.create(destinatario=self.user, mensaje="Test estados")
        
        # Probar leída
        noti.leida = True
        noti.save()
        self.assertTrue(Notificacion.objects.get(pk=noti.pk).leida)
        
        # Probar silenciada
        noti.silenciada = True
        noti.save()
        self.assertTrue(Notificacion.objects.get(pk=noti.pk).silenciada)

    def test_notificacion_diferentes_usuarios(self):
        user2 = User.objects.create_user(email="user2@test.com", password="pass123")
        
        noti1 = Notificacion.objects.create(destinatario=self.user, mensaje="Para user1")
        noti2 = Notificacion.objects.create(destinatario=user2, mensaje="Para user2")
        
        # Verificar que cada notificación pertenece al usuario correcto
        self.assertEqual(noti1.destinatario, self.user)
        self.assertEqual(noti2.destinatario, user2)