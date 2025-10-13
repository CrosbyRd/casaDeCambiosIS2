from typing import Optional
from clientes.models import Cliente
from django.contrib.auth import get_user_model # <- AGREGAR ESTA LÍNEA

SESSION_KEY = "cliente_activo_id"

def get_cliente_activo(request) -> Optional[Cliente]:
    """Devuelve el Cliente activo del usuario o None."""
    user = request.user
    if not user.is_authenticated:
        return None
    
    # 🚨 SOLUCIÓN FINAL: Forzar la carga de una instancia 'fresca' de CustomUser
    # Esto bypassa la instancia 'request.user' cacheada en memoria.
    try:
        User = get_user_model()
        user_fresh = User.objects.get(pk=request.user.pk)
    except User.DoesNotExist:
        # Esto no debería pasar, pero es buena práctica
        return None 
    
    user = user_fresh # Ahora 'user' es la instancia correcta.
    
    # 2. si hay uno en sesión y pertenece al usuario, úsalo
    cliente_id = request.session.get(SESSION_KEY)
    if cliente_id:
        try:
            return user.clientes.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            request.session.pop(SESSION_KEY, None)

    # 3. si el usuario tiene exactamente 1 cliente, seleccionarlo por defecto
    qs = user.clientes.all()
    if qs.count() == 1:
        cliente = qs.first()
        request.session[SESSION_KEY] = str(cliente.pk)
        return cliente

    # 4. ninguno o varios → forzar selección explícita
    return None
