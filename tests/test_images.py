from app.core.config import settings
from app.modules.images.api.routes import has_valid_signature
from app.modules.images.infrastructure.storage import SupabaseImageStorage


def test_image_signatures() -> None:
    assert has_valid_signature(b"\xff\xd8\xffdata", "image/jpeg")
    assert has_valid_signature(b"\x89PNG\r\n\x1a\ndata", "image/png")
    assert has_valid_signature(b"RIFF0000WEBPdata", "image/webp")
    assert not has_valid_signature(b"<script>alert(1)</script>", "image/png")


def test_only_managed_urls_are_resolved(monkeypatch) -> None:
    monkeypatch.setattr(settings, "supabase_url", "https://project.supabase.co")
    monkeypatch.setattr(settings, "supabase_key", "test-key")
    monkeypatch.setattr(settings, "supabase_storage_bucket", "El Bisne Imagenes")
    storage = SupabaseImageStorage()
    managed = (
        "https://grejlkqaqqvygendoko.supabase.co/storage/v1/object/public/"
        "El%20Bisne%20Imagenes/businesses/123/logo/image.png"
    )
    assert storage.path_from_public_url(managed) == "businesses/123/logo/image.png"
    assert storage.path_from_public_url("https://example.com/image.png") is None
