"""Storage factories for Supabase Storage with a local-disk fallback.

Use as a callable on model fields so the correct backend is chosen from
settings:

    logo = models.ImageField(upload_to="logos/", storage=public_storage)
    document = models.FileField(upload_to="docs/", storage=private_storage)

Public bucket: files are served from stable public URLs (school logos).
Private bucket: files are only reachable through short-lived signed URLs
(documents, contracts, receipts).
"""
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage


def s3_configured():
    """True when Supabase S3 credentials are present in settings."""
    return bool(
        getattr(settings, "SUPABASE_S3_ENDPOINT", "")
        and getattr(settings, "SUPABASE_S3_ACCESS_KEY_ID", "")
        and getattr(settings, "SUPABASE_S3_SECRET_ACCESS_KEY", "")
    )


def _s3_options(bucket_name):
    return {
        "bucket_name": bucket_name,
        "endpoint_url": settings.SUPABASE_S3_ENDPOINT,
        "access_key": settings.SUPABASE_S3_ACCESS_KEY_ID,
        "secret_key": settings.SUPABASE_S3_SECRET_ACCESS_KEY,
        "region_name": settings.SUPABASE_S3_REGION,
        "signature_version": "s3v4",
        "addressing_style": "path",
        "default_acl": None,
        "file_overwrite": False,
    }


def public_storage():
    """Storage for files that may be shown to anyone (logos, badges)."""
    if not s3_configured():
        return FileSystemStorage(
            location=str(settings.MEDIA_ROOT / "public"),
            base_url=f"{settings.MEDIA_URL}public/",
        )
    bucket = settings.SUPABASE_PUBLIC_BUCKET
    options = _s3_options(bucket)
    options["querystring_auth"] = False
    host = urlparse(getattr(settings, "SUPABASE_URL", "")).netloc
    if host:
        options["custom_domain"] = f"{host}/storage/v1/object/public/{bucket}"
    return S3Storage(**options)


def private_storage():
    """Storage for restricted files, served only through signed URLs."""
    if not s3_configured():
        return FileSystemStorage(
            location=str(settings.MEDIA_ROOT / "private"),
            base_url=f"{settings.MEDIA_URL}private/",
        )
    options = _s3_options(settings.SUPABASE_PRIVATE_BUCKET)
    options["querystring_auth"] = True
    options["querystring_expire"] = settings.SUPABASE_SIGNED_URL_SECONDS
    return S3Storage(**options)
