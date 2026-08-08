import asyncio
from typing import Any
from urllib.parse import quote, unquote

from supabase import Client, create_client

from app.core.config import settings
from app.shared.domain.exceptions import ValidationError


class SupabaseImageStorage:
    def __init__(self) -> None:
        if (
            not settings.supabase_url
            or not settings.supabase_key
            or not settings.supabase_storage_bucket
        ):
            raise ValidationError("Supabase Storage is not configured")
        self.bucket_name = settings.supabase_storage_bucket
        self.client: Client = create_client(settings.supabase_url, settings.supabase_key)

    def _bucket(self) -> Any:
        return self.client.storage.from_(self.bucket_name)

    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        bucket = self._bucket()
        await asyncio.to_thread(
            bucket.upload,
            path,
            content,
            {"content-type": content_type, "upsert": "false"},
        )
        return bucket.get_public_url(path)

    async def delete(self, path: str) -> None:
        await asyncio.to_thread(self._bucket().remove, [path])

    async def delete_prefix(self, prefix: str) -> None:
        def collect(folder: str) -> list[str]:
            paths: list[str] = []
            for item in self._bucket().list(folder, {"limit": 1000, "offset": 0}):
                item_path = f"{folder}/{item['name']}"
                if item.get("metadata") is None:
                    paths.extend(collect(item_path))
                else:
                    paths.append(item_path)
            return paths

        paths = await asyncio.to_thread(collect, prefix.rstrip("/"))
        if paths:
            await asyncio.to_thread(self._bucket().remove, paths)

    def path_from_public_url(self, url: str | None) -> str | None:
        if not url:
            return None
        encoded_bucket = quote(self.bucket_name, safe="")
        for bucket in (encoded_bucket, self.bucket_name):
            marker = f"/storage/v1/object/public/{bucket}/"
            if marker in url:
                return unquote(url.split(marker, 1)[1])
        return None
