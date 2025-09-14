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

class CustomUser(AbstractBaseUser, PermissionsMixin):

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=False) # Inicia inactivo hasta verificar
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # campos para  verificacion con OTP
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    code_created_at = models.DateTimeField(blank=True, null=True)

    # relaciona customUser con Role (N:M)
    roles = models.ManyToManyField(Role, blank=True)

    def get_all_permissions(self, obj=None):
        # permisos estándar (user_permissions + groups)
        perms = super().get_all_permissions(obj)

        # permisos heredados de roles
        role_perms = self.roles.values_list(
            "permissions__content_type__app_label",
            "permissions__codename"
        )
        role_perms = {f"{ct}.{name}" for ct, name in role_perms}

        return perms.union(role_perms)

    def has_perm(self, perm, obj=None):
        return perm in self.get_all_permissions(obj)

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

    # Genera un código de 6 dígitos y marca la hora de creación
    def generate_verification_code(self):
        """Genera un código de 6 dígitos y guarda el momento de creación."""
        self.verification_code = str(random.randint(100000, 999999))
        self.code_created_at = timezone.now()
        self.save()

    # verifica que el codigo sea correcto
    def is_code_valid(self, code, minutes_valid=1):     #el codigo expira en 1 minuto
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
    

class UsuariosPermissions(models.Model):
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ("access_user_client_management", "Puede gestionar usuarios y clientes"),
        ]
