# --- Borrar usuarios por email (directo) ---
from django.contrib.auth import get_user_model

User = get_user_model()

# 1) EDITÁ esta lista con los correos a borrar (puede estar vacía al inicio)
EMAILS = [

    "globalexchange2@gmail.com",
]

# 2) Si querés borrar también staff/superusers, poné True (¡cuidado!)
FORCE = False

# --- No toques de acá para abajo ---
emails_norm = [e.strip().lower() for e in EMAILS if e and e.strip()]
qs = User.objects.filter(email__in=emails_norm)
if not FORCE:
    qs = qs.exclude(is_superuser=True).exclude(is_staff=True)

to_delete = list(qs.values_list('email', flat=True))
print(f"Se borrarán {len(to_delete)} usuario(s):")
for e in to_delete:
    print("  -", e)

deleted_count, per_model = qs.delete()
print(f"[OK] Eliminados: {deleted_count} registro(s) en total.")
print("[Detalle por modelo]:", per_model)
