"""
Manejo seguro de adjuntos en disco (Opción A).

Los archivos se guardan bajo backend/storage/<subdir>/<empresa>/ con un nombre
ÚNICO y SANITIZADO (uuid + nombre original saneado). La BD solo guarda la ruta
server-relative (p. ej. 'storage/cotizaciones/PFX/uuid_archivo.pdf'), nunca la
ruta absoluta ni el nombre crudo del usuario. Sin path traversal.

Convención de almacenamiento igual a las actas/bajas (backend/storage/...),
carpeta ya incluida en .gitignore.
"""
import os
import re
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile

BASE_DIR = Path(__file__).parent.parent          # backend/
STORAGE_ROOT = BASE_DIR / "storage"

# Tipos permitidos (por extensión) + límite de tamaño
ALLOWED_EXT = {"pdf", "png", "jpg", "jpeg", "eml", "msg"}
MAX_BYTES = 10 * 1024 * 1024                      # 10 MB

_SAFE_RX = re.compile(r"[^A-Za-z0-9._-]")


def _sanitizar_nombre(nombre: str) -> str:
    """Devuelve un nombre de archivo seguro: solo basename, sin separadores de
    ruta, caracteres permitidos [A-Za-z0-9._-], longitud acotada."""
    base = os.path.basename(nombre or "")         # descarta cualquier ruta
    base = base.replace("\\", "").replace("/", "")
    base = _SAFE_RX.sub("_", base).strip("._") or "archivo"
    return base[:120]


def _extension(nombre: str) -> str:
    return (os.path.splitext(nombre or "")[1].lstrip(".") or "").lower()


def guardar_adjunto(upload: UploadFile, subdir: str, empresa_key: str) -> dict:
    """Valida (tipo + tamaño) y guarda el archivo en disco.
    Devuelve {archivo_nombre, archivo_path (server-relative), archivo_tipo}.
    Lanza HTTPException 400 si el tipo o el tamaño no son válidos."""
    nombre_original = upload.filename or "archivo"
    ext = _extension(nombre_original)
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido (.{ext or '?'}). Permitidos: {', '.join(sorted(ALLOWED_EXT))}")

    contenido = upload.file.read()                # lee en memoria (límite 10 MB)
    if len(contenido) == 0:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(contenido) > MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo supera el límite de {MAX_BYTES // (1024 * 1024)} MB")

    # Carpeta destino (creada on-demand); empresa_key saneada para el path
    carpeta_key = _SAFE_RX.sub("_", (empresa_key or "GEN"))[:40] or "GEN"
    dest_dir = STORAGE_ROOT / subdir / carpeta_key
    dest_dir.mkdir(parents=True, exist_ok=True)

    nombre_seguro = f"{uuid.uuid4().hex}_{_sanitizar_nombre(nombre_original)}"
    if not nombre_seguro.lower().endswith(f".{ext}"):
        nombre_seguro = f"{nombre_seguro}.{ext}"
    destino = dest_dir / nombre_seguro
    with open(destino, "wb") as f:
        f.write(contenido)

    # Ruta server-relative (para BD + FileResponse(BASE_DIR / path))
    archivo_path = f"storage/{subdir}/{carpeta_key}/{nombre_seguro}"
    return {
        "archivo_nombre": _sanitizar_nombre(nombre_original),
        "archivo_path": archivo_path,
        "archivo_tipo": upload.content_type or ext,
    }


def ruta_absoluta(archivo_path: str) -> Path:
    """Resuelve una ruta server-relative a absoluta, garantizando que quede
    DENTRO de STORAGE_ROOT (defensa anti path traversal). Lanza 404 si no."""
    if not archivo_path:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    abs_path = (BASE_DIR / archivo_path).resolve()
    try:
        abs_path.relative_to(STORAGE_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ruta de archivo inválida")
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor")
    return abs_path


def eliminar_adjunto(archivo_path: str) -> None:
    """Elimina el archivo del disco si existe y está dentro de STORAGE_ROOT.
    No lanza si ya no existe (idempotente)."""
    if not archivo_path:
        return
    try:
        abs_path = (BASE_DIR / archivo_path).resolve()
        abs_path.relative_to(STORAGE_ROOT.resolve())
    except ValueError:
        return
    if abs_path.is_file():
        abs_path.unlink()
