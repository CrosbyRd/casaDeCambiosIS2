from abc import ABC, abstractmethod
from django.http import HttpRequest
from transacciones.models import Transaccion

class BasePaymentGateway(ABC):
    """
    Clase base abstracta para todas las pasarelas de pago.
    Define la interfaz común que cada pasarela debe implementar.
    """

    @abstractmethod
    def initiate_payment(self, transaccion: Transaccion, request: HttpRequest) -> str:
        """
        Inicia un proceso de pago para una transacción dada.
        Debe devolver la URL a la que el cliente debe ser redirigido para completar el pago.
        """
        pass

    @abstractmethod
    def handle_webhook(self, payload: dict) -> dict:
        """
        Maneja una notificación de webhook de la pasarela de pago.
        Debe procesar el payload y devolver un diccionario con el estado de la transacción.
        """
        pass
