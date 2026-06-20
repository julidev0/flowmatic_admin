import bcrypt
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User as DjangoUser
from django.db import IntegrityError
from .models import Usuario


class SpringBootAuthBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        if not email or not password:
            return None

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return None
        except Exception:
            return None

        if not usuario.activo or not usuario.clave:
            return None

        try:
            clave_bytes = usuario.clave.encode('utf-8')
            password_bytes = password.encode('utf-8')
            if not bcrypt.checkpw(password_bytes, clave_bytes):
                return None
        except Exception:
            return None

        try:
            django_user, created = DjangoUser.objects.get_or_create(
                username=usuario.email,
                defaults={
                    'email': usuario.email,
                    'first_name': usuario.username,
                    'last_name': usuario.apellido,
                }
            )

            if not created:
                django_user.first_name = usuario.username
                django_user.last_name = usuario.apellido
                django_user.email = usuario.email

            django_user.set_unusable_password()
            django_user.is_active = True
            django_user.is_staff = True
            django_user.save()
        except IntegrityError:
            return None

        return django_user

    def get_user(self, user_id):
        try:
            return DjangoUser.objects.get(pk=user_id)
        except DjangoUser.DoesNotExist:
            return None
