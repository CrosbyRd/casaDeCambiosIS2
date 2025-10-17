# /home/richar-carballo/Escritorio/IS2/casaDeCambiosIS2/CasaDeCambioIS2/celery.py (NUEVO ARCHIVO)
import os
from celery import Celery

# Establece el módulo de settings de Django para el programa 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CasaDeCambioIS2.settings')

app = Celery('CasaDeCambioIS2')

# Usar un string aquí significa que el worker no necesita serializar
# el objeto de configuración. El namespace 'CELERY' significa que todas las
# variables de configuración de Celery deben tener el prefijo `CELERY_`.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carga automáticamente los módulos de tasks.py de todas las apps registradas.
app.autodiscover_tasks()