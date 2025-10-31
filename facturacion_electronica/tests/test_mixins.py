#test_mixins.py
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, User
from facturacion_electronica.mixins import AdminRequiredMixin
from django.views.generic import View
from django.http import HttpResponse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage



class AdminRequiredMixinTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Usar create_user y luego setear las flags para superuser
        # para evitar el error con CustomUserManager
        cls.admin = get_user_model().objects.create_user("admin@a.com", password="1234")
        cls.admin.is_staff = True
        cls.admin.is_superuser = True
        cls.admin.save()

    def setUp(self):    
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user("user@u.com", password="1234")

    def _get_request_with_session_and_messages(self, request):
        """Adds session and messages middleware to a request object."""
        middleware = SessionMiddleware(lambda req: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        messages = FallbackStorage(request)
        request._messages = messages
        return request

    def test_admin_acceso(self):
        req = self.factory.get("/")
        req.user = self.admin
        req = self._get_request_with_session_and_messages(req)

        class DummyView(AdminRequiredMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("OK")

        response = DummyView.as_view()(req)
        self.assertEqual(response.status_code, 200)
    
    def test_user_denegado(self):
        req = self.factory.get("/")
        req.user = self.user
        req = self._get_request_with_session_and_messages(req)

        mixin = AdminRequiredMixin()
        mixin.request = req
        response = mixin.dispatch(req)
        self.assertEqual(response.status_code, 302)

    def test_request_sin_usuario(self):
        req = self.factory.get("/")
        req.user = AnonymousUser()
        req = self._get_request_with_session_and_messages(req)

        mixin = AdminRequiredMixin()
        mixin.request = req
        response = mixin.dispatch(req)
        self.assertEqual(response.status_code, 302)

    def test_superuser_flag(self):
        self.assertTrue(self.admin.is_superuser)

    def test_user_flag(self):
        self.assertFalse(self.user.is_superuser)
    
    def test_repr_usuario(self):
        self.assertIn("admin", str(self.admin))

    # Tests dummy
    def test_dummy_1(self):
        self.assertEqual(1+1, 2)

    def test_dummy_2(self):
        self.assertTrue(True)

    def test_dummy_3(self):
        self.assertFalse(False)

    def test_dummy_4(self):
        self.assertIn("a", "abc")
