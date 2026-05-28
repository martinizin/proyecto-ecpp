"""
DRF Serializers for the Academico bounded context.

Provides read/write representations of academic models for the REST API.
Refs: AC-PER-06, AC-CAT-07
"""

from django.conf import settings
from rest_framework import serializers

from apps.academico.domain.exceptions import AcademicoError
from apps.academico.domain.services import AsignaturaService, ParaleloService, PeriodoService
from apps.academico.infrastructure.models import (
    Asignatura,
    AsignaturaLicencia,
    Paralelo,
    Periodo,
    TipoLicencia,
)
from apps.academico.presentation.exception_mapping import to_drf


class TipoLicenciaSerializer(serializers.ModelSerializer):
    """Read-only serializer for license types (C, E, EC)."""

    class Meta:
        model = TipoLicencia
        fields = [
            "id",
            "nombre",
            "codigo",
            "duracion_meses",
            "num_asignaturas",
            "activo",
        ]
        read_only_fields = fields


class PeriodoSerializer(serializers.ModelSerializer):
    """
    Serializer for academic periods.

    - Read: includes all fields + creado_por username.
    - Write: nombre, fecha_inicio, fecha_fin only (activo managed via activation endpoint).
    """

    creado_por_nombre = serializers.CharField(
        source="creado_por.get_full_name",
        read_only=True,
        default="",
    )
    tipo_licencia_codigo = serializers.CharField(
        source="tipo_licencia.codigo",
        read_only=True,
    )

    class Meta:
        model = Periodo
        fields = [
            "id",
            "nombre",
            "tipo_licencia",
            "tipo_licencia_codigo",
            "fecha_inicio",
            "fecha_fin",
            "activo",
            "creado_por",
            "creado_por_nombre",
            "modificado_en",
        ]
        read_only_fields = [
            "id",
            "activo",
            "creado_por",
            "creado_por_nombre",
            "tipo_licencia_codigo",
            "modificado_en",
        ]

    def validate(self, attrs):
        fecha_inicio = attrs.get("fecha_inicio")
        fecha_fin = attrs.get("fecha_fin")
        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha de fin debe ser posterior a la fecha de inicio."}
            )
        if fecha_inicio and fecha_fin:
            try:
                PeriodoService().validar_duracion(
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    minimo=settings.PERIODO_DURACION_MIN_MESES,
                    maximo=settings.PERIODO_DURACION_MAX_MESES,
                )
            except AcademicoError as e:
                raise to_drf(e, field="fecha_fin")
        return attrs


class AsignaturaLicenciaSerializer(serializers.ModelSerializer):
    """Nested serializer for per-license-type hours."""

    tipo_licencia_id = serializers.IntegerField()
    tipo_licencia_codigo = serializers.CharField(source="tipo_licencia.codigo", read_only=True)

    class Meta:
        model = AsignaturaLicencia
        fields = ["tipo_licencia_id", "tipo_licencia_codigo", "horas_lectivas"]


class AsignaturaSerializer(serializers.ModelSerializer):
    """
    Serializer for subjects.

    - Read: licencias as nested objects with tipo_licencia detail.
    - Write: licencias as list of {tipo_licencia_id, horas_lectivas}.
    """

    licencias = AsignaturaLicenciaSerializer(source="asignatura_licencias", many=True)
    tipos_licencia_detail = TipoLicenciaSerializer(
        source="tipos_licencia",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Asignatura
        fields = [
            "id",
            "nombre",
            "codigo",
            "descripcion",
            "licencias",
            "tipos_licencia_detail",
        ]

    def validate_licencias(self, value):
        if not value:
            raise serializers.ValidationError("Debe asignar al menos un tipo de licencia.")
        
        service = AsignaturaService()
        for entry in value:
            horas = entry.get("horas_lectivas", 0)
            try:
                service.validar_horas_lectivas(
                    horas=horas,
                    maximo=settings.HORAS_LECTIVAS_MAX
                )
            except Exception as e:
                # Translate domain exception to DRF error routed to 'licencias' field
                raise to_drf(e, field="licencias")
        
        return value

    def create(self, validated_data):
        licencias_data = validated_data.pop("asignatura_licencias", [])
        asignatura = Asignatura.objects.create(**validated_data)
        AsignaturaLicencia.objects.bulk_create(
            [
                AsignaturaLicencia(
                    asignatura=asignatura,
                    tipo_licencia_id=lic["tipo_licencia_id"],
                    horas_lectivas=lic["horas_lectivas"],
                )
                for lic in licencias_data
            ]
        )
        return asignatura

    def update(self, instance, validated_data):
        licencias_data = validated_data.pop("asignatura_licencias", [])
        instance.nombre = validated_data.get("nombre", instance.nombre)
        instance.codigo = validated_data.get("codigo", instance.codigo)
        instance.descripcion = validated_data.get("descripcion", instance.descripcion)
        instance.save()
        instance.asignatura_licencias.all().delete()
        AsignaturaLicencia.objects.bulk_create(
            [
                AsignaturaLicencia(
                    asignatura=instance,
                    tipo_licencia_id=lic["tipo_licencia_id"],
                    horas_lectivas=lic["horas_lectivas"],
                )
                for lic in licencias_data
            ]
        )
        return instance


class ParaleloSerializer(serializers.ModelSerializer):
    """
    Serializer for class sections (parallels).

    - Read: nested asignatura, periodo, tipo_licencia, docente info.
    - Write: FK IDs directly.
    """

    asignatura_nombre = serializers.CharField(
        source="asignatura.nombre",
        read_only=True,
    )
    periodo_nombre = serializers.CharField(
        source="periodo.nombre",
        read_only=True,
    )
    tipo_licencia_codigo = serializers.CharField(
        source="tipo_licencia.codigo",
        read_only=True,
    )
    docente_nombre = serializers.CharField(
        source="docente.get_full_name",
        read_only=True,
    )

    class Meta:
        model = Paralelo
        fields = [
            "id",
            "asignatura",
            "asignatura_nombre",
            "periodo",
            "periodo_nombre",
            "tipo_licencia",
            "tipo_licencia_codigo",
            "docente",
            "docente_nombre",
            "nombre",
            "capacidad_maxima",
        ]

    def validate_capacidad_maxima(self, value):
        try:
            ParaleloService().validar_capacidad(
                capacidad=value,
                maximo=settings.PARALELO_CAPACIDAD_MAXIMA,
            )
        except AcademicoError as e:
            raise to_drf(e, field="capacidad_maxima")
        return value
