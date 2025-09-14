from django.db import models

# Create your models here.
class AdminPanelPermissions(models.Model):
    class Meta:
        managed = False    #no guarda en la base de datos 
        default_permissions = ()
        permissions = [
            ("access_admin_dashboard", "Puede acceder al dashboard del Admin Panel"),    #crea un permiso django permissions llamado access_admin_dashboard
        ]
