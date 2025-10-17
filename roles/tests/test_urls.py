# roles/tests/test_urls_roles.py
from django.test import SimpleTestCase
from django.urls import reverse, resolve
from roles import views

class TestUrls(SimpleTestCase):
    def test_role_panel_url_resolves(self):
        url = reverse("roles:role-panel")
        self.assertEqual(resolve(url).func, views.role_panel)

    def test_manage_user_roles_url_resolves(self):
        url = reverse("roles:manage-user-roles", args=[1])
        self.assertEqual(resolve(url).func, views.manage_user_roles)
