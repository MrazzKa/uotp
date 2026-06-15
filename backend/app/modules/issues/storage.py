import uuid
from datetime import timedelta
from io import BytesIO

import anyio
from fastapi import HTTPException, UploadFile, status
from minio import Minio
from PIL import ExifTags, Image

from app.config import settings

# MIME types we accept for attachments. The real type is detected from the bytes,
# not trusted from the client-supplied Content-Type.
ALLOWED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
PDF_MAGIC = b"%PDF-"


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )


def ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def presigned_url(value: str | None) -> str | None:
    """Return a short-lived presigned GET URL for a stored object key.

    Values that are already absolute URLs (e.g. seeded/external placeholders) are
    passed through unchanged.
    """
    if not value:
        return value
    if value.startswith("http://") or value.startswith("https://"):
        return value
    client = get_minio_client()
    return client.presigned_get_object(
        settings.minio_bucket, value, expires=timedelta(seconds=settings.attachment_url_ttl)
    )


def detect_mime(source: bytes) -> str:
    """Detect a supported MIME from the bytes; raise 400 otherwise."""
    if source[:5] == PDF_MAGIC:
        return "application/pdf"
    try:
        with Image.open(BytesIO(source)) as image:
            fmt = image.format
    except Exception:
        fmt = None
    if fmt in ALLOWED_IMAGE_FORMATS:
        return ALLOWED_IMAGE_FORMATS[fmt]
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Unsupported file type (allowed: JPEG, PNG, WEBP, PDF)",
    )


def image_bytes(source: bytes, max_size: tuple[int, int]) -> bytes:
    image = Image.open(BytesIO(source))
    image.thumbnail(max_size)
    target = BytesIO()
    image.convert("RGB").save(target, format="JPEG", quality=82)
    return target.getvalue()


def extract_exif(source: bytes) -> dict:
    try:
        image = Image.open(BytesIO(source))
        raw = image.getexif()
    except Exception:
        return {}
    result = {}
    for key, value in raw.items():
        name = ExifTags.TAGS.get(key, str(key))
        try:
            result[name] = str(value)
        except Exception:
            result[name] = "<unreadable>"
    return result


def perceptual_hash(source: bytes) -> str | None:
    try:
        image = Image.open(BytesIO(source)).convert("L").resize((8, 8))
    except Exception:
        return None
    pixels = list(image.getdata())
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if pixel > average else "0" for pixel in pixels)
    return f"{int(bits, 2):016x}"


def _store_object(client: Minio, key: str, data: bytes, content_type: str) -> None:
    client.put_object(settings.minio_bucket, key, BytesIO(data), length=len(data), content_type=content_type)


def _upload_sync(tenant_id: uuid.UUID, issue_id: uuid.UUID, original: bytes, content_type: str) -> dict:
    """Blocking MinIO + image work; executed in a worker thread."""
    client = get_minio_client()
    ensure_bucket(client)
    is_image = content_type.startswith("image/")
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "application/pdf": "pdf"}.get(
        content_type, "bin"
    )
    base_key = f"{tenant_id}/issues/{issue_id}/{uuid.uuid4().hex}"
    original_key = f"{base_key}/original.{ext}"
    _store_object(client, original_key, original, content_type)

    medium_key = None
    thumbnail_key = None
    if is_image:
        medium = image_bytes(original, (1280, 1280))
        thumbnail = image_bytes(original, (320, 320))
        medium_key = f"{base_key}/medium.jpg"
        thumbnail_key = f"{base_key}/thumbnail.jpg"
        _store_object(client, medium_key, medium, "image/jpeg")
        _store_object(client, thumbnail_key, thumbnail, "image/jpeg")

    return {
        # Object keys are stored; presigned URLs are generated on read.
        "file_url": original_key,
        "medium_url": medium_key,
        "thumbnail_url": thumbnail_key,
        "mime_type": content_type,
        "size_bytes": len(original),
        "raw_exif": extract_exif(original) if is_image else {},
        "perceptual_hash": perceptual_hash(original) if is_image else None,
    }


async def upload_issue_file(tenant_id: uuid.UUID, issue_id: uuid.UUID, file: UploadFile) -> dict:
    original = await file.read()
    if not original:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(original) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large"
        )
    content_type = detect_mime(original)
    return await anyio.to_thread.run_sync(_upload_sync, tenant_id, issue_id, original, content_type)
