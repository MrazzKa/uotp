from io import BytesIO

import pytest
from fastapi import HTTPException
from PIL import Image

from app.modules.issues.storage import detect_mime, presigned_url


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (4, 4), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def test_detect_mime_accepts_png() -> None:
    assert detect_mime(_png_bytes()) == "image/png"


def test_detect_mime_accepts_pdf_magic() -> None:
    assert detect_mime(b"%PDF-1.7\n...") == "application/pdf"


def test_detect_mime_rejects_unknown() -> None:
    with pytest.raises(HTTPException) as exc:
        detect_mime(b"not a real image or pdf")
    assert exc.value.status_code == 415


def test_presigned_url_passes_through_absolute_urls() -> None:
    url = "https://placehold.co/1200x800"
    assert presigned_url(url) == url
    assert presigned_url(None) is None
