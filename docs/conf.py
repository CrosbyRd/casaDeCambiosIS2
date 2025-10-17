# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys
import django

# Añadir el directorio raíz del proyecto (donde se encuentra manage.py) al sys.path
# Esto asume que conf.py está en casaDeCambiosIS2/docs/
# La ruta correcta para que Django encuentre las apps es el directorio que contiene el paquete principal (casaDeCambiosIS2)
# La ruta correcta para que Django encuentre las apps es el directorio que contiene el paquete principal (casaDeCambiosIS2)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'casaDeCambiosIS2'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CasaDeCambioIS2.settings')
django.setup()

# Para depuración:
print(f"DEBUG: sys.path = {sys.path}")
print(f"DEBUG: DJANGO_SETTINGS_MODULE = {os.environ.get('DJANGO_SETTINGS_MODULE')}")

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'CasaDeCambioIS2 Documentation'
copyright = '2025, Diego'
author = 'Diego'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_rtd_theme',
    'sphinx_autodoc_typehints'
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'es'

# Opciones para autodoc
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
