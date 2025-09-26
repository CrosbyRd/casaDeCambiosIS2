from django.test import SimpleTestCase
from django.urls import reverse, resolve
from medios_acreditacion import views
import uuid

class TestMediosAcreditacionUrls(SimpleTestCase):

    def test_urls_resuelven(self):
        urls_views = {
            "medios_acreditacion:clientes_list": views.MedioClienteListView,
            "medios_acreditacion:clientes_create": views.MedioClienteCreateView,
            "medios_acreditacion:clientes_update": views.MedioClienteUpdateView,
            "medios_acreditacion:clientes_delete": views.MedioClienteDeleteView,
        }
        for name, view in urls_views.items():
            args = [uuid.uuid4()] if "update" in name or "delete" in name else []
            url = reverse(name, args=args)
            resolved = resolve(url)
            self.assertEqual(resolved.func.view_class, view, msg=f"La URL {name} debería resolverse a {view.__name__}")
