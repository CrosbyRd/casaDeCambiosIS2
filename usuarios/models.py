from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from roles.models import Role
from clientes.models import Cliente # MERGE: Importamos el modelo Cliente de la rama entrante
import random
from datetime import timedelta

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):

    class UserTypes(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        ANALISTA = 'ANALISTA', 'Analista'
        CLIENTE = 'CLIENTE', 'Cliente'


    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=False) # Inicia inactivo hasta verificar
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # MERGE: Campos para la verificación por código de tu rama (HEAD)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    code_created_at = models.DateTimeField(blank=True, null=True)

    # MERGE: Relación ManyToMany con Role (más flexible que ForeignKey)
    roles = models.ManyToManyField(Role, blank=True)

    # MERGE: Relación ManyToMany con Cliente de la rama entrante
    clientes = models.ManyToManyField(
        Cliente,
        blank=True,
        related_name='usuarios'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

    # MERGE: Métodos para manejar la lógica de verificación de tu rama (HEAD)
    def generate_verification_code(self):
        """Genera un código de 6 dígitos y guarda el momento de creación."""
        self.verification_code = str(random.randint(100000, 999999))
        self.code_created_at = timezone.now()
        self.save()

    def is_code_valid(self, code, minutes_valid=5):
        """Verifica si el código es correcto y no ha expirado."""
        if self.verification_code != code:
            return False
        if self.code_created_at:
            expiration_time = self.code_created_at + timedelta(minutes=minutes_valid)
            return timezone.now() <= expiration_time
        return False

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        if self.is_active and self.is_superuser:
            return True

        # Primero, revisamos los permisos a nivel de usuario
        # Esto es importante para mantener la compatibilidad con los permisos directos
        if super().has_perm(perm, obj):
            return True

        # Si no, verificamos si alguno de sus roles tiene el permiso
        # 'perm' tiene el formato "app_label.codename"
        try:
            app_label, codename = perm.split('.')
        except ValueError:
            return False

        return self.roles.filter(
            permissions__content_type__app_label=app_label,
            permissions__codename=codename
        ).exists()

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        if self.is_active and self.is_superuser:
            return True
        
        if super().has_module_perms(app_label):
            return True

        return self.roles.filter(permissions__content_type__app_label=app_label).exists()
