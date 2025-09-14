import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


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
