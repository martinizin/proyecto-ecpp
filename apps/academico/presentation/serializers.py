"""
DRF Serializers for the Academico bounded context.

Provides read/write representations of academic models for the REST API.
Refs: AC-PER-06, AC-CAT-07
"""

from rest_framework import serializers

from apps.academico.infrastructure.models import (
    Asignatura,
    Paralelo,
    Periodo,
    TipoLicencia,
)


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

    class Meta:
        model = Periodo
        fields = [
            "id",
            "nombre",
            "fecha_inicio",
            "fecha_fin",
            "activo",
            "creado_por",
            "creado_por_nombre",
            "modificado_en",
        ]
        read_only_fields = ["id", "activo", "creado_por", "creado_por_nombre", "modificado_en"]

    def validate(self, attrs):
        fecha_inicio = attrs.get("fecha_inicio")
        fecha_fin = attrs.get("fecha_fin")
        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha de fin debe ser posterior a la fecha de inicio."}
            )
        return attrs


class AsignaturaSerializer(serializers.ModelSerializer):
    """
    Serializer for subjects.

    - Read: tipos_licencia as nested objects.
    - Write: tipos_licencia as list of IDs (PrimaryKeyRelatedField).
    """

    tipos_licencia = serializers.PrimaryKeyRelatedField(
        queryset=TipoLicencia.objects.filter(activo=True),
        many=True,
    )
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
            "horas_lectivas",
            "tipos_licencia",
            "tipos_licencia_detail",
        ]

    def validate_horas_lectivas(self, value):
        if value <= 0:
            raise serializers.ValidationError("Las horas lectivas deben ser mayores a 0.")
        return value

    def validate_tipos_licencia(self, value):
        if not value:
            raise serializers.ValidationError(
                "Debe asignar al menos un tipo de licencia."
            )
        return value


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
            "horario",
            "capacidad_maxima",
        ]

    def validate_capacidad_maxima(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La capacidad máxima debe ser mayor a 0."
            )
        return value
