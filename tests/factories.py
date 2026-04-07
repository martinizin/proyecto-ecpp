"""
Factory-boy factories for all ECPPP models.
Used in tests to create consistent, reproducible test data.
"""

import datetime
from decimal import Decimal

import factory
from django.utils import timezone

from apps.academico.infrastructure.models import Asignatura, Paralelo, Periodo, TipoLicencia
from apps.asistencia.infrastructure.models import Asistencia
from apps.calificaciones.infrastructure.models import Calificacion, Evaluacion
from apps.solicitudes.infrastructure.models import Solicitud
from apps.usuarios.infrastructure.models import OTPToken, RegistroAuditoria, Usuario


class UsuarioFactory(factory.django.DjangoModelFactory):
    """Factory for Usuario model."""

    class Meta:
        model = Usuario
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"usuario{n}")
    first_name = factory.Faker("first_name", locale="es")
    last_name = factory.Faker("last_name", locale="es")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@test.com")
    cedula = factory.Sequence(lambda n: f"{1700000000 + n}")
    rol = Usuario.Rol.ESTUDIANTE
    is_active = True
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class EstudianteFactory(UsuarioFactory):
    """Factory for student users."""

    rol = Usuario.Rol.ESTUDIANTE
    username = factory.Sequence(lambda n: f"estudiante{n}")


class DocenteFactory(UsuarioFactory):
    """Factory for teacher users."""

    rol = Usuario.Rol.DOCENTE
    username = factory.Sequence(lambda n: f"docente{n}")


class InspectorFactory(UsuarioFactory):
    """Factory for inspector users."""

    rol = Usuario.Rol.INSPECTOR
    username = factory.Sequence(lambda n: f"inspector{n}")


class OTPTokenFactory(factory.django.DjangoModelFactory):
    """Factory for OTPToken model."""

    class Meta:
        model = OTPToken

    usuario = factory.SubFactory(UsuarioFactory)
    codigo = factory.Sequence(lambda n: f"{100000 + n}")
    expira_en = factory.LazyFunction(
        lambda: timezone.now() + datetime.timedelta(minutes=10)
    )
    usado = False


class RegistroAuditoriaFactory(factory.django.DjangoModelFactory):
    """Factory for RegistroAuditoria model."""

    class Meta:
        model = RegistroAuditoria

    usuario = factory.SubFactory(UsuarioFactory)
    accion = "login_exitoso"
    ip = "127.0.0.1"
    detalle = ""


class TipoLicenciaFactory(factory.django.DjangoModelFactory):
    """Factory for TipoLicencia model."""

    class Meta:
        model = TipoLicencia

    nombre = factory.Sequence(lambda n: f"Tipo Licencia {n}")
    codigo = factory.Sequence(lambda n: f"T{n}")
    duracion_meses = 6
    num_asignaturas = 10
    activo = True


class PeriodoFactory(factory.django.DjangoModelFactory):
    """Factory for Periodo model."""

    class Meta:
        model = Periodo

    nombre = factory.Sequence(lambda n: f"2026-{n}")
    fecha_inicio = factory.LazyFunction(lambda: datetime.date(2026, 3, 1))
    fecha_fin = factory.LazyFunction(lambda: datetime.date(2026, 7, 31))
    activo = True


class AsignaturaFactory(factory.django.DjangoModelFactory):
    """Factory for Asignatura model."""

    class Meta:
        model = Asignatura
        skip_postgeneration_save = True

    nombre = factory.Sequence(lambda n: f"Asignatura {n}")
    codigo = factory.Sequence(lambda n: f"ASG-{n:03d}")
    descripcion = "Descripcion de prueba"
    horas_lectivas = 40

    @factory.post_generation
    def tipos_licencia(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.tipos_licencia.set(extracted)


class ParaleloFactory(factory.django.DjangoModelFactory):
    """Factory for Paralelo model."""

    class Meta:
        model = Paralelo

    asignatura = factory.SubFactory(AsignaturaFactory)
    periodo = factory.SubFactory(PeriodoFactory)
    tipo_licencia = factory.SubFactory(TipoLicenciaFactory)
    docente = factory.SubFactory(DocenteFactory)
    nombre = factory.Sequence(lambda n: chr(65 + (n % 26)))  # A, B, C, ...
    horario = "Lunes 08:00 - 10:00"
    capacidad_maxima = 30


class EvaluacionFactory(factory.django.DjangoModelFactory):
    """Factory for Evaluacion model."""

    class Meta:
        model = Evaluacion

    paralelo = factory.SubFactory(ParaleloFactory)
    tipo = Evaluacion.TipoEvaluacion.PARCIAL_1
    peso = Decimal("25.00")
    fecha = factory.LazyFunction(lambda: datetime.date(2026, 4, 15))


class CalificacionFactory(factory.django.DjangoModelFactory):
    """Factory for Calificacion model."""

    class Meta:
        model = Calificacion

    evaluacion = factory.SubFactory(EvaluacionFactory)
    estudiante = factory.SubFactory(EstudianteFactory)
    nota = Decimal("8.50")


class AsistenciaFactory(factory.django.DjangoModelFactory):
    """Factory for Asistencia model."""

    class Meta:
        model = Asistencia

    estudiante = factory.SubFactory(EstudianteFactory)
    paralelo = factory.SubFactory(ParaleloFactory)
    fecha = factory.LazyFunction(lambda: datetime.date(2026, 4, 1))
    estado = Asistencia.Estado.PRESENTE


class SolicitudFactory(factory.django.DjangoModelFactory):
    """Factory for Solicitud model."""

    class Meta:
        model = Solicitud

    tipo = Solicitud.TipoSolicitud.RECTIFICACION
    estudiante = factory.SubFactory(EstudianteFactory)
    estado = Solicitud.EstadoSolicitud.PENDIENTE
    descripcion = "Solicitud de prueba"
