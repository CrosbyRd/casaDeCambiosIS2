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
    
    correo_electronico = models.EmailField(
        unique=True,
        verbose_name=_('Correo electrónico verificado')
    )
    
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.MINORISTA,
        verbose_name=_('Categoría del cliente')
    )
    
    

    # Atributo de bonificación (se calcula automáticamente)
    @property
    def bonificacion(self):
        """
        Devuelve el porcentaje de bonificación según la categoría del cliente
        """
        bonificaciones = {
            self.Categoria.VIP: Decimal('10.0'),      # 10% para VIP
            self.Categoria.CORPORATIVO: Decimal('5.0'), # 5% para Corporativo
            self.Categoria.MINORISTA: Decimal('0.0')   # 0% para Minorista
        }
        return bonificaciones.get(self.categoria, Decimal('0.0'))
    
    # Límites de compra por moneda (se calculan automáticamente)
    @property
    def limite_compra_usd(self):
        """
        Devuelve el límite de compra en USD según la categoría del cliente
        """
        limites_usd = {
            self.Categoria.VIP: Decimal('50000.00'),      # A DEFINIR
            self.Categoria.CORPORATIVO: Decimal('25000.00'), # A DEFINIR
            self.Categoria.MINORISTA: Decimal('5000.00')    # A DEFINIR
        }
        return limites_usd.get(self.categoria, Decimal('0.00'))
    def obtener_limite_compra(self, moneda):
        """
        Devuelve el límite de compra para una moneda específica
        """
        limites = {
            'USD': self.limite_compra_usd,
            'EUR': self.limite_compra_eur,
            'BRL': self.limite_compra_brl,
            'PYG': self.limite_compra_pyg  # Podemos agregar más monedas
        }
        return limites.get(moneda.upper(), Decimal('0.00'))
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
    ##CLASES SUGERIDAS POR LA IA 
    class Meta:
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.correo_electronico}) - {self.get_categoria_display()}"
    
    def esta_activo(self):
        return self.activo
    
    def puede_comprar(self, moneda, monto):
        """
        Verifica si el cliente puede realizar una compra del monto especificado
        """
        limite = self.obtener_limite_compra(moneda)
        return monto <= limite, f"Límite: {limite} {moneda}"
    


