import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from operaciones.models import CanalFinanciero
from configuracion.models import TransactionLimit

class Cliente(models.Model):
    class Categoria(models.TextChoices):
        MINORISTA = 'minorista', _('Minorista')
        CORPORATIVO = 'corporativo', _('Corporativo')
        VIP = 'vip', _('VIP')
    
    # Atributos básicos
    id_cliente = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID del cliente')
    )
    
    nombre = models.CharField(
        max_length=200,
        verbose_name=_('Nombre completo o razón social')
    )
    
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.MINORISTA,
        verbose_name=_('Categoría del cliente')
    )

    activo = models.BooleanField(
        default=True,
        verbose_name=_('Cliente activo')
    )
    
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de registro')
    )
    
    ultima_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última modificación')
    )

    # -----------------------------
    # Propiedades calculadas
    # -----------------------------
    @property
    def bonificacion(self):
        """Devuelve el porcentaje de bonificación según la categoría del cliente."""
        bonificaciones = {
            self.Categoria.VIP: Decimal('10.0'),      
            self.Categoria.CORPORATIVO: Decimal('5.0'),
            self.Categoria.MINORISTA: Decimal('0.0')
        }
        return bonificaciones.get(self.categoria, Decimal('0.0'))
    
    @property
    def limite_compra_usd(self):
        """Devuelve el límite de compra en USD según la categoría del cliente."""
        limites_usd = {
            self.Categoria.VIP: Decimal('50000.00'),
            self.Categoria.CORPORATIVO: Decimal('25000.00'),
            self.Categoria.MINORISTA: Decimal('5000.00')
        }
        return limites_usd.get(self.categoria, Decimal('0.00'))

    def obtener_limite_compra(self, moneda):
        """Devuelve el límite de compra para una moneda específica."""
        limites = {
            'USD': self.limite_compra_usd,
            # Si después quieres, puedes definir límites específicos para EUR, BRL, PYG
        }
        return limites.get(moneda.upper(), Decimal('0.00'))


    @property
    def obtener_limite_global(self):
        """
        Obtiene el límite global de transacciones para el cliente.
        """
        limite = TransactionLimit.objects.first()  # Obtiene el primer límite global
        if limite:
            return limite.monto_diario, limite.monto_mensual
        return Decimal('0.00'), Decimal('0.00')  # Si no existe límite global, retorna 0
    
    # -----------------------------
    # Meta y representación
    # -----------------------------
    class Meta:
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')
        ordering = ['nombre']
        permissions = [
        ("access_clientes_panel", "Puede acceder al panel de clientes"),
    ]
    
    def __str__(self):
        return f"{self.nombre} - {self.get_categoria_display()}"
    
    def esta_activo(self):
        return self.activo
    
    def puede_comprar(self, moneda, monto):
        """Verifica si el cliente puede realizar una compra del monto especificado."""
        limite = self.obtener_limite_compra(moneda)
        return monto <= limite, f"Límite: {limite} {moneda}"


class MedioAcreditacion(models.Model):
    """
    Almacena un medio de acreditación de un cliente.
    Está directamente vinculado a un CanalFinanciero que la empresa soporta.
    """
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medios_acreditacion')
    
    # El cliente debe elegir entre los canales que la empresa tiene configurados.
    canal = models.ForeignKey(CanalFinanciero, on_delete=models.PROTECT, help_text="Entidad financiera soportada por la casa de cambio.")
    
    identificador = models.CharField(max_length=100, help_text="Ej: Número de cuenta, CBU, Número de Teléfono, etc.")
    alias = models.CharField(max_length=50, blank=True, null=True, help_text="Un nombre fácil de recordar para este medio.")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cliente.username} - {self.canal.nombre} ({self.alias or self.identificador})"

    class Meta:
        verbose_name = "Medio de Acreditación"
        verbose_name_plural = "Medios de Acreditación"
        # Un cliente no puede tener el mismo identificador dos veces para el mismo canal.
        unique_together = ('cliente', 'canal', 'identificador')
