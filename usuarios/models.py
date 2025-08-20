# usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from roles.models import Role 

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    roles = models.ManyToManyField(
        Role,
        verbose_name="Roles",
        blank=True,
        related_name="users"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email