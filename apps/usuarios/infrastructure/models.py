from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Custom user model extending AbstractUser.
    Adds role-based access (estudiante, docente, inspector) and Ecuadorian ID fields.
    """

    class Rol(models.TextChoices):
        ESTUDIANTE = "estudiante", "Estudiante"
        DOCENTE = "docente", "Docente"
        INSPECTOR = "inspector", "Inspector"

    rol = models.CharField(max_length=20, choices=Rol.choices)
    cedula = models.CharField(max_length=13, unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name()} ({self.rol})"
