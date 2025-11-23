from django.urls import reverse, resolve
from configuracion import views

def test_url_lista_limites():
    url = reverse("configuracion:lista_limites")
    assert resolve(url).func == views.lista_limites

    # ERROR INTENCIONAL: usar nombre inexistente
    # url = reverse("configuracion:limite_inexistente")  # esto rompe con NoReverseMatch
    # resolve(url)

def test_url_crear_limite():
    url = reverse("configuracion:crear_limite")
    assert resolve(url).func == views.crear_limite

def test_url_editar_limite():
    url = reverse("configuracion:editar_limite", args=[1])
    assert resolve(url).func == views.editar_limite

def test_url_eliminar_limite():
    url = reverse("configuracion:eliminar_limite", args=[1])
    assert resolve(url).func == views.eliminar_limite
