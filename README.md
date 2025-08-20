# Proyecto Casa de Cambio IS2

Este documento es una guía paso a paso para configurar el entorno de desarrollo local y poder colaborar en el proyecto.

## Prerrequisitos

Antes de comenzar, asegúrate de tener instalado lo siguiente en tu sistema:
* **Git:** Para clonar el repositorio.
* **Python 3.10 o superior:** Incluyendo `pip` y `venv`.

Puedes verificar si los tienes con `git --version` y `python3 --version`.

Si te falta `pip` o `venv`, puedes instalarlos con el siguiente comando:
```bash
sudo apt update
sudo apt install python3-pip python3-venv
```

---

## Pasos para la Configuración del Entorno Local

Sigue estos pasos en orden. Se asume que estás usando una terminal en un sistema operativo basado en Debian (Ubuntu, Linux Mint, etc.).

### 1. Clonar el Repositorio

Primero, clona el código fuente del proyecto desde el repositorio de Git en tu máquina.

```bash
# Reemplaza la URL con la de nuestro repositorio
git clone <URL_DEL_REPOSITORIO_GIT>

# Navega a la carpeta del proyecto recién clonado
cd <NOMBRE_DE_LA_CARPETA_DEL_PROYECTO>
```

### 2. Crear y Activar el Entorno Virtual

Siempre trabajaremos dentro de un entorno virtual para aislar las dependencias del proyecto.

```bash
# Crear el entorno virtual (se creará una carpeta llamada "venv")
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate
```
> **Nota:** Verás `(venv)` al principio de la línea de tu terminal. Esto indica que el entorno está activo. Para desactivarlo, simplemente escribe `deactivate`.

### 3. Instalar y Configurar PostgreSQL

Nuestro proyecto utiliza PostgreSQL como base de datos para simular un entorno más realista y facilitar la colaboración.

**a) Instalar PostgreSQL:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib

# Iniciar y asegurar que el servicio se ejecute al arrancar el sistema
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**b) Crear la Base de Datos y el Usuario del Proyecto:**
Ahora, vamos a crear una base de datos y un usuario dedicados exclusivamente para este proyecto.

```bash
# Acceder a la consola de PostgreSQL como superusuario
sudo -u postgres psql
```

Una vez dentro de `psql` (la terminal cambiará a `postgres=#`), ejecuta los siguientes comandos SQL:

```sql
-- 1. Crea la base de datos (puedes copiar y pegar el bloque completo)
CREATE DATABASE casadecambio_db;

-- 2. Crea el usuario que usará Django para conectarse
--    ¡IMPORTANTE! Usa la misma contraseña que está configurada en el settings.py
CREATE USER casadecambio_user WITH PASSWORD 'una_contraseña_muy_segura';

-- 3. Dale al nuevo usuario la propiedad de la base de datos (esto le da todos los permisos necesarios)
ALTER DATABASE casadecambio_db OWNER TO casadecambio_user;

-- 4. Sal de la consola de psql
\q
```
> **¡Atención!** La contraseña que uses aquí **debe ser exactamente la misma** que está configurada en el archivo `settings.py` del proyecto para que la conexión funcione.

### 4. Instalar las Dependencias de Python

Con el entorno virtual aún activo, instala todas las librerías que el proyecto necesita. Estas están listadas en el archivo `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 5. Aplicar las Migraciones

Las migraciones son las instrucciones que construyen la estructura de nuestra base de datos (tablas, columnas, etc.).

```bash
python manage.py migrate
```

### 6. Crear un Superusuario Local

Necesitarás un usuario administrador para poder acceder al panel de Django en `/admin`.

```bash
python manage.py createsuperuser
```
Sigue las instrucciones para crear tu nombre de usuario, email y contraseña.

### 7. Ejecutar el Servidor de Desarrollo

¡Todo está listo! Ahora puedes ejecutar el proyecto.

```bash
python manage.py runserver
```

Abre tu navegador web y ve a **`http://127.0.0.1:8000/`** para ver la aplicación funcionando.

---

## Flujo de Trabajo Diario

Para mantener tu proyecto actualizado con los cambios del resto del equipo, sigue esta rutina:

1.  **Activa siempre tu entorno virtual:** `source venv/bin/activate`
2.  **Trae los últimos cambios del repositorio:** `git pull`
3.  **Aplica nuevas migraciones (si las hay):** `python manage.py migrate`
4.  **Instala nuevas dependencias (si las hay):** `pip install -r requirements.txt`
5.  **Ejecuta el servidor:** `python manage.py runserver`
