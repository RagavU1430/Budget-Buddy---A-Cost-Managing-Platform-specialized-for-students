"""Report file storage.

Django stored report files with ``FileField(upload_to="reports/%Y/%m/")``.
This module reproduces the resulting object key (``reports/2026/11/monthly-2026-11.pdf``)
and keeps the same collision behaviour (Django appends a 7-character random
suffix before the extension when the name is taken).

Two backends are supported:

``local``     files under ``LOCAL_STORAGE_DIR`` — used for dev and tests.
``supabase``  the Supabase Storage S3 endpoint, via ``boto3``. The bucket is
              private; downloads are streamed by the API, never by public URL.

Both are synchronous engines, so every call is pushed to a worker thread.
"""

from __future__ import annotations

import asyncio
import mimetypes
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

_FILENAME_ALPHABET = string.ascii_letters + string.digits


class StorageError(RuntimeError):
    """Raised when a report file cannot be written or read."""


def object_key(filename: str, *, at: datetime | None = None) -> str:
    """``upload_to="reports/%Y/%m/"`` — timestamped in UTC like the deploy host."""
    moment = at or datetime.now(timezone.utc)
    return f"reports/{moment:%Y}/{moment:%m}/{filename}"


def _split_filename(filename: str) -> tuple[str, str]:
    stem, dot, extension = filename.rpartition(".")
    if not dot:
        return filename, ""
    return stem, f".{extension}"


def _candidate_keys(filename: str) -> str:
    """Random suffix mirrors ``django.core.files.storage.get_available_name``."""
    stem, extension = _split_filename(filename)
    suffix = "".join(secrets.choice(_FILENAME_ALPHABET) for _ in range(7))
    return f"{stem}_{suffix}{extension}"


def _local_path(key: str) -> Path:
    parts = key.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise StorageError(f"Invalid storage key: {key!r}")
    return Path(settings.LOCAL_STORAGE_DIR).joinpath(*parts)


# ---------------------------------------------------------------------------
# Local filesystem
# ---------------------------------------------------------------------------
def _local_save(filename: str, content: bytes) -> str:
    key = object_key(filename)
    path = _local_path(key)
    while path.exists():
        key = object_key(_candidate_keys(filename))
        path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return key


def _local_read(key: str) -> bytes:
    path = _local_path(key)
    if not path.is_file():
        raise FileNotFoundError(key)
    return path.read_bytes()


def _local_delete(key: str) -> None:
    path = _local_path(key)
    if path.is_file():
        path.unlink()


# ---------------------------------------------------------------------------
# Supabase Storage (S3-compatible)
# ---------------------------------------------------------------------------
def _s3_client():
    import boto3
    from botocore.config import Config

    if not settings.SUPABASE_S3_ENDPOINT:
        raise StorageError("SUPABASE_S3_ENDPOINT is not configured.")
    return boto3.client(
        "s3",
        endpoint_url=settings.SUPABASE_S3_ENDPOINT,
        region_name=settings.SUPABASE_S3_REGION,
        aws_access_key_id=settings.SUPABASE_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SUPABASE_S3_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def _s3_exists(client, key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        client.head_object(Bucket=settings.SUPABASE_STORAGE_BUCKET, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def _s3_save(filename: str, content: bytes) -> str:
    client = _s3_client()
    key = object_key(filename)
    while _s3_exists(client, key):
        key = object_key(_candidate_keys(filename))
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    client.put_object(
        Bucket=settings.SUPABASE_STORAGE_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    return key


def _s3_read(key: str) -> bytes:
    client = _s3_client()
    response = client.get_object(Bucket=settings.SUPABASE_STORAGE_BUCKET, Key=key)
    return response["Body"].read()


def _s3_delete(key: str) -> None:
    _s3_client().delete_object(Bucket=settings.SUPABASE_STORAGE_BUCKET, Key=key)


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------
def _using_supabase() -> bool:
    return settings.STORAGE_BACKEND.strip().lower() == "supabase"


async def save_report(filename: str, content: bytes) -> str:
    """Persist ``content`` and return the storage key stored in ``Report.file``."""
    if _using_supabase():
        return await asyncio.to_thread(_s3_save, filename, content)
    return await asyncio.to_thread(_local_save, filename, content)


async def read_report(key: str) -> bytes:
    """Read a report back for the authenticated download endpoint."""
    if _using_supabase():
        return await asyncio.to_thread(_s3_read, key)
    return await asyncio.to_thread(_local_read, key)


async def delete_report(key: str) -> None:
    """Remove an orphaned object (used when the DB insert fails after upload)."""
    if _using_supabase():
        await asyncio.to_thread(_s3_delete, key)
    else:
        await asyncio.to_thread(_local_delete, key)


def download_filename(key: str) -> str:
    """Django's ``report.file.name.rsplit("/", 1)[-1]``."""
    return key.rsplit("/", 1)[-1]


def ensure_local_media_root() -> None:
    """Create ``./media`` once at startup so the first download works."""
    if not _using_supabase():
        Path(settings.LOCAL_STORAGE_DIR).mkdir(parents=True, exist_ok=True)


__all__ = [
    "StorageError",
    "delete_report",
    "download_filename",
    "ensure_local_media_root",
    "object_key",
    "read_report",
    "save_report",
]
