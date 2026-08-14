"""
Ascendra — Storage Provider ABC.
"""

from abc import ABC, abstractmethod


class StorageProvider(ABC):

    @abstractmethod
    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        """Upload a file and return its public/signed URL."""
        ...

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download a file."""
        ...

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """Get a signed/public URL for a file."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file."""
        ...
