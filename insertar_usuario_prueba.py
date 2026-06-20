"""
Script para insertar un usuario de prueba en la base de datos.
Ejecutar DESPUÉS de haber creado la BD y la tabla con PgAdmin4.

Uso:
    python insertar_usuario_prueba.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import bcrypt
from admin_panel.models import Usuario

# --- DATOS DEL USUARIO DE PRUEBA ---
EMAIL = "admin@flowmatic.com"
CLAVE = "123456"
NOMBRE = "Admin"
APELLIDO = "Flowmatic"
ROL = "ROLE_RRHH"

# Verificar si ya existe
if Usuario.objects.filter(email=EMAIL).exists():
    print(f"El usuario {EMAIL} ya existe.")
else:
    clave_hash = bcrypt.hashpw(CLAVE.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    usuario = Usuario(
        username=NOMBRE,
        apellido=APELLIDO,
        email=EMAIL,
        clave=clave_hash,
        telefono=None,
        rol=ROL,
        activo=True,
        tokenactivacion=None,
        estado="Activo",
    )
    usuario.save()
    print(f"Usuario {EMAIL} creado exitosamente.")
    print(f"Email: {EMAIL}")
    print(f"Contraseña: {CLAVE}")
