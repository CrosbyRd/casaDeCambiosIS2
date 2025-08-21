from django.contrib import admin
from .models import CustomUser, Rol, Permiso, EmailLoginCode

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "tipo_usuario", "is_active", "is_staff")
    list_filter = ("tipo_usuario", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)

@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo")
    search_fields = ("nombre", "codigo")

@admin.register(EmailLoginCode)
class EmailLoginCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "mfa_token", "used", "attempts", "expires_at", "created_at")
    list_filter = ("used",)
    search_fields = ("user__username", "user__email", "mfa_token")
    readonly_fields = ("created_at",)
