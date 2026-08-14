"""
Ascendra — Supabase Storage Provider.

Uses Supabase Storage (S3-compatible) for file storage.
Free tier: 1GB storage, 2GB bandwidth.
"""

import logging

from app.config import settings
from app.providers.storage.base import StorageProvider

logger = logging.getLogger("ascendra.providers.storage.supabase")


class SupabaseStorageProvider(StorageProvider):

    def __init__(self):
        self._client = None

    def _get_client(self):
        if not self._client:
            from supabase import create_client
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return self._client

    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        """Upload a file to Supabase Storage."""
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.warning("Supabase not configured — storing locally")
            return path

        try:
            client = self._get_client()
            bucket = settings.SUPABASE_STORAGE_BUCKET
            client.storage.from_(bucket).upload(
                path=path,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            logger.info(f"File uploaded: {path}")
            return path
        except Exception as e:
            logger.error(f"Supabase upload failed: {e}")
            raise

    async def download(self, path: str) -> bytes:
        """Download a file from Supabase Storage."""
        client = self._get_client()
        bucket = settings.SUPABASE_STORAGE_BUCKET
        response = client.storage.from_(bucket).download(path)
        return response

    async def get_url(self, path: str) -> str:
        """Get a signed URL for a file (1 hour expiry)."""
        client = self._get_client()
        bucket = settings.SUPABASE_STORAGE_BUCKET
        response = client.storage.from_(bucket).create_signed_url(path, 3600)
        return response.get("signedURL", "")

    async def delete(self, path: str) -> None:
        """Delete a file from Supabase Storage."""
        client = self._get_client()
        bucket = settings.SUPABASE_STORAGE_BUCKET
        client.storage.from_(bucket).remove([path])

    async def delete_many(self, paths: list[str]) -> None:
        """Delete multiple files from Supabase Storage in 1 batch request."""
        if not paths:
            return
        client = self._get_client()
        bucket = settings.SUPABASE_STORAGE_BUCKET
        client.storage.from_(bucket).remove(paths)


storage_provider = SupabaseStorageProvider()
