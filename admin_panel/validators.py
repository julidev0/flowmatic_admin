import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
UUID_REGEX = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)

FIELD_MAX_LENGTH = {
    'username': 100,
    'apellido': 100,
    'email': 254,
    'clave': 128,
    'telefono': 20,
    'token': 36,
}


def validar_email(email):
    if not email or not EMAIL_REGEX.match(email):
        return 'Ingresa un correo electrónico válido.'
    return None


def validar_password(pwd):
    errores = []
    if not pwd:
        return ['La contraseña es obligatoria.']
    if len(pwd) < 8:
        errores.append('Al menos 8 caracteres.')
    if len(pwd) > FIELD_MAX_LENGTH['clave']:
        errores.append(f'Máximo {FIELD_MAX_LENGTH["clave"]} caracteres.')
    if not re.search(r'[A-Z]', pwd):
        errores.append('Al menos una letra mayúscula.')
    if not re.search(r'[a-z]', pwd):
        errores.append('Al menos una letra minúscula.')
    if not re.search(r'\d', pwd):
        errores.append('Al menos un dígito.')
    return errores if errores else None


def validar_uuid(token):
    if not token or not UUID_REGEX.match(token):
        return 'El enlace no es válido o ha expirado.'
    return None


def validar_longitud(campo, valor):
    max_len = FIELD_MAX_LENGTH.get(campo)
    if max_len and valor and len(valor) > max_len:
        return f'El campo {campo} no puede exceder {max_len} caracteres.'
    return None
