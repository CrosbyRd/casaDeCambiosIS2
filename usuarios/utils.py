from typing import Optional
from clientes.models import Cliente

SESSION_KEY = "cliente_activo_id"

def get_cliente_activo(request) -> Optional[Cliente]:
    """Devuelve el Cliente activo del usuario o None."""
    user = request.user
    if not user.is_authenticated:
        return None

    # 1) si hay uno en sesión y pertenece al usuario, úsalo
    cliente_id = request.session.get(SESSION_KEY)
    if cliente_id:
        try:
            return user.clientes.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            request.session.pop(SESSION_KEY, None)

    # 2) si el usuario tiene exactamente 1 cliente, seleccionarlo por defecto
    qs = user.clientes.all()
    if qs.count() == 1:
        cliente = qs.first()
        request.session[SESSION_KEY] = str(cliente.pk)
        return cliente

    # 3) ninguno o varios → forzar selección explícita
    return None
