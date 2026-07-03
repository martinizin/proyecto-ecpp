from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MANUALS_DIR = ROOT / "docs" / "manuales"
ASSETS_DIR = MANUALS_DIR / "assets"


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_manual_files_and_asset_structure_exist():
    required_files = [
        MANUALS_DIR / "architecture-manual.md",
        MANUALS_DIR / "database-manual.md",
        MANUALS_DIR / "user-manual.md",
        ASSETS_DIR / "README.md",
        ASSETS_DIR / "user" / "README.md",
    ]
    required_dirs = [
        ASSETS_DIR / "architecture",
        ASSETS_DIR / "database",
        ASSETS_DIR / "user",
    ]

    for path in required_files:
        assert path.exists(), f"Missing documentation artifact: {path.relative_to(ROOT)}"

    for path in required_dirs:
        assert path.exists() and path.is_dir(), f"Missing asset directory: {path.relative_to(ROOT)}"


@pytest.mark.parametrize(
    ("manual_name", "expected_fragments"),
    [
        (
            "architecture-manual.md",
            [
                "Metadatos",
                "Propósito",
                "Contextos delimitados",
                "Fronteras de capa",
                "Dirección de dependencias",
                "Convenciones de nombres",
                "Rama fuente",
                "Último snapshot revisado",
                "Ver también",
            ],
        ),
        (
            "database-manual.md",
            [
                "Metadatos",
                "Inventario principal de modelos",
                "Relaciones entre apps",
                "Invariantes a preservar",
                "Usuarios",
                "Calificaciones",
                "AUTH_USER_MODEL",
                "Ver también",
            ],
        ),
        (
            "user-manual.md",
            [
                "Metadatos",
                "Flujo de estudiante",
                "Flujo de docente",
                "Flujo de secretaría",
                "Flujo de inspectoría",
                "Marcadores de capturas",
                "docs/manuales/assets/user",
                "Ver también",
            ],
        ),
    ],
)
def test_manuals_include_required_sections(manual_name, expected_fragments):
    text = _read(f"docs/manuales/{manual_name}")
    for fragment in expected_fragments:
        assert fragment in text, f"{manual_name} is missing '{fragment}'"


def test_readme_documents_manuals_and_cross_links():
    readme = _read("README.md")
    expected_links = [
        "## Documentación",
        "docs/manuales/architecture-manual.md",
        "docs/manuales/database-manual.md",
        "docs/manuales/user-manual.md",
        "docs/manuales/assets/README.md",
    ]

    for fragment in expected_links:
        assert fragment in readme, f"README.md is missing '{fragment}'"
