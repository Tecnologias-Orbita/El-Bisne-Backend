import re
import unicodedata

from app.shared.domain.exceptions import ValidationError


def normalize_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if not 3 <= len(slug) <= 100:
        raise ValidationError("Slug must contain between 3 and 100 valid characters")
    return slug
