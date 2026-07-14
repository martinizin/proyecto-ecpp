"""Guard: el contenido de la aplicación se escribe en español neutro (Issue 9).

El producto es para una escuela de conducción ecuatoriana; el voseo rioplatense
("Seleccioná", "Querés", "Hacé clic") es dialectal y no corresponde. Este test
falla si alguna forma voseante vuelve a entrar en templates o en el código.

Cubre las dos marcas inequívocas del voseo:
- Imperativo con acento en la última sílaba: "Seleccioná", "Revisá", "Escribí".
- Presente de indicativo: "querés", "podés", "tenés", "sabés".

NO marca futuros ni terceras personas ("generará", "deberá", "será"), que son
español neutro perfectamente válido.
"""

import re
from pathlib import Path

import pytest
from django.conf import settings


BASE = Path(settings.BASE_DIR)
RAICES = [BASE / "templates", BASE / "apps"]

# Raíz SIN la vocal final: el acento agudo de cierre es lo que delata al voseo
# ("selecciona" es neutro; "seleccioná" no lo es).
_RAICES_IMPERATIVAS = (
    "hac|seleccion|reseleccion|revis|adjunt|verific|escrib|respond|report|prob"
    "|marc|intent|ingres|complet|guard|eleg|envi|descarg|record|consult|confirm"
    "|aplic|esper|establec"
)

_VOSEO = re.compile(
    # Imperativo voseante: raíz + vocal acentuada final.
    rf"\b(?:{_RAICES_IMPERATIVAS})(?:á|é|í)\b"
    # Presente de indicativo voseante.
    r"|\b(?:quer[eé]s|pod[eé]s|ten[eé]s|sab[eé]s|deb[eé]s|hac[eé]s)\b",
    re.IGNORECASE,
)


def _archivos():
    for raiz in RAICES:
        for patron in ("*.html", "*.py"):
            for path in raiz.rglob(patron):
                if "__pycache__" in path.parts or "migrations" in path.parts:
                    continue
                yield path


@pytest.mark.parametrize("archivo", sorted(_archivos()), ids=lambda p: p.name)
def test_sin_voseo_rioplatense(archivo):
    hallazgos = []
    for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), start=1):
        for match in _VOSEO.finditer(linea):
            hallazgos.append(f"  línea {numero}: {match.group(0)!r} → {linea.strip()[:80]}")

    assert not hallazgos, (
        f"{archivo.relative_to(BASE)} usa voseo rioplatense; "
        "el contenido va en español neutro:\n" + "\n".join(hallazgos)
    )
