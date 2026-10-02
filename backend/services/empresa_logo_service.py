"""
Gestión del LOGO de cada empresa — MISMA convención que ya usan las actas.

Las actas resuelven el logo por convención de nombre en disco:
    backend/templates/img/logo_{prefijo}.png
(ver services.pdf_service.get_logo_base64). Este servicio ALIMENTA ese mismo
archivo — no crea un segundo almacén — validando la imagen subida y
convirtiéndola a PNG. Ese directorio también lo publica la ruta estática
/logos-empresa (main.py). Así, un logo cargado aquí aparece en las actas de la
empresa sin ningún paso extra.
"""
import io
import re
from pathlib import Path
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

BASE_DIR  = Path(__file__).parent.parent          # backend/
LOGOS_DIR = BASE_DIR / "templates" / "img"        # donde leen las actas

# Imágenes permitidas (por extensión) + límite de tamaño
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "bmp", "webp"}
MAX_BYTES   = 5 * 1024 * 1024                      # 5 MB (un logo no necesita más)

_SAFE_RX = re.compile(r"[^A-Za-z0-9]")


def _prefijo_seguro(prefijo: str) -> str:
    """Prefijo saneado y en mayúsculas, apto para nombre de archivo."""
    p = _SAFE_RX.sub("", (prefijo or "").upper())[:5]
    if not p:
        raise HTTPException(status_code=400, detail="Prefijo inválido para el logo")
    return p


def logo_path(prefijo: str) -> Path:
    """Ruta del logo de la empresa: templates/img/logo_{prefijo}.png."""
    return LOGOS_DIR / f"logo_{_prefijo_seguro(prefijo)}.png"


def tiene_logo(prefijo: str) -> bool:
    """True si existe el archivo de logo para ese prefijo (lo que leen las actas)."""
    try:
        return logo_path(prefijo).is_file()
    except HTTPException:
        return False


def _extension(nombre: str) -> str:
    return (Path(nombre or "").suffix.lstrip(".") or "").lower()


def validar_y_convertir(upload: UploadFile) -> bytes:
    """Valida que sea una imagen (extensión + contenido real) y la convierte a
    PNG. Devuelve los bytes PNG listos para escribir. Lanza HTTPException 400 si
    el tipo, el tamaño o el contenido no son válidos."""
    if not upload or not upload.filename:
        raise HTTPException(status_code=400, detail="Debe adjuntar una imagen para el logo")
    ext = _extension(upload.filename)
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de imagen no permitido (.{ext or '?'}). Permitidos: {', '.join(sorted(ALLOWED_EXT))}")

    contenido = upload.file.read()                # lee en memoria (límite 5 MB)
    if len(contenido) == 0:
        raise HTTPException(status_code=400, detail="El archivo del logo está vacío")
    if len(contenido) > MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"El logo supera el límite de {MAX_BYTES // (1024 * 1024)} MB")

    # Verificación de contenido real: no basta la extensión.
    try:
        Image.open(io.BytesIO(contenido)).verify()          # ¿es imagen válida?
        img = Image.open(io.BytesIO(contenido)).convert("RGBA")  # reabrir tras verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida")

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def escribir_logo(prefijo: str, png_bytes: bytes) -> None:
    """Escribe el PNG en templates/img/logo_{prefijo}.png (donde leen las actas).
    Sobrescribe el existente si lo hay."""
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    with open(logo_path(prefijo), "wb") as f:
        f.write(png_bytes)


def eliminar_logo(prefijo: str) -> None:
    """Borra el logo de una empresa si existe (idempotente)."""
    try:
        p = logo_path(prefijo)
    except HTTPException:
        return
    if p.is_file():
        p.unlink()


def renombrar_logo(prefijo_viejo: str, prefijo_nuevo: str) -> None:
    """Al cambiar el prefijo, mueve logo_{viejo}.png → logo_{nuevo}.png para que
    las actas (que resuelven por prefijo) sigan encontrándolo y no quede huérfano.
    Idempotente: no hace nada si no hay archivo o si el prefijo no cambió."""
    if not prefijo_viejo or not prefijo_nuevo:
        return
    try:
        if _prefijo_seguro(prefijo_viejo) == _prefijo_seguro(prefijo_nuevo):
            return
        viejo = logo_path(prefijo_viejo)
        if viejo.is_file():
            LOGOS_DIR.mkdir(parents=True, exist_ok=True)
            viejo.replace(logo_path(prefijo_nuevo))
    except HTTPException:
        return
