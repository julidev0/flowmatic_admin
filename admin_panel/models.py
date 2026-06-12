from django.db import models


class Usuario(models.Model):
    username = models.TextField()
    apellido = models.TextField()
    email = models.TextField(unique=True)
    clave = models.TextField()
    telefono = models.TextField(blank=True, null=True)
    rol = models.TextField()
    activo = models.BooleanField()
    tokenactivacion = models.TextField(unique=True, blank=True, null=True)
    estado = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.username} {self.apellido} ({self.email})"
