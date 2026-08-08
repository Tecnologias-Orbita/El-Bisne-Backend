import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.db.session import async_session_factory, engine
from app.modules.auth.infrastructure.models.user import UserModel
from app.modules.billing.domain.plans import SubscriptionPlan
from app.modules.billing.infrastructure.models.billing import (
    ExchangeRateModel,
    PlatformPaymentSettingsModel,
    SubscriptionPaymentModel,
)
from app.modules.businesses.infrastructure.models.business import (
    BusinessMemberModel,
    BusinessModel,
)
from app.modules.catalog.infrastructure.models.catalog import CategoryModel, ProductModel
from app.modules.platform_categories.infrastructure.models.platform_category import (
    PlatformCategoryModel,
)
from app.modules.services.infrastructure.models.service import ServiceModel
from app.modules.sites.infrastructure.models.site import BusinessSiteModel
from app.shared.infrastructure.security import hash_password

ADMIN_EMAIL = "admin@elbisne.dev"
ADMIN_PASSWORD = "Admin123!"
OWNER_EMAIL = "owner.demo@elbisne.dev"
OWNER_PASSWORD = "Demo123!"
SECOND_OWNER_EMAIL = "dulce.alma@elbisne.dev"
SECOND_OWNER_PASSWORD = "Dulce123!"

UNSPLASH = "https://images.unsplash.com/"
IMAGES = {
    "coffee": f"{UNSPLASH}photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=1200&q=85",
    "latte": f"{UNSPLASH}photo-1572442388796-11668a67e53d?auto=format&fit=crop&w=1200&q=85",
    "croissant": f"{UNSPLASH}photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=1200&q=85",
    "cake": f"{UNSPLASH}photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=1200&q=85",
    "cupcake": f"{UNSPLASH}photo-1486427944299-d1955d23e34d?auto=format&fit=crop&w=1200&q=85",
    "bread": f"{UNSPLASH}photo-1509440159596-0249088772ff?auto=format&fit=crop&w=1200&q=85",
    "burger": f"{UNSPLASH}photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=1200&q=85",
    "pizza": f"{UNSPLASH}photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=1200&q=85",
    "sandwich": f"{UNSPLASH}photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=1200&q=85",
    "tacos": f"{UNSPLASH}photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=1200&q=85",
}

PLATFORM_CATEGORIES = (
    ("Restaurantes", "restaurantes", "Comida preparada y experiencias gastronómicas."),
    ("Cafeterías", "cafeterias", "Café, bebidas y meriendas."),
    ("Dulces y panadería", "dulces-panaderia", "Repostería, panes y encargos dulces."),
)

BUSINESSES: tuple[dict[str, Any], ...] = (
    {
        "owner_email": OWNER_EMAIL,
        "name": "Café Bisne Demo",
        "slug": "cafe-bisne-demo",
        "description": (
            "Café de barrio con desayunos, meriendas y platos preparados al momento. "
            "Un espacio cálido para compartir sabores cubanos y propuestas contemporáneas."
        ),
        "sells_online": False,
        "contact_phone": "+5351111111",
        "platform_category": "restaurantes",
        "hero": IMAGES["burger"],
        "logo": IMAGES["coffee"],
        "payment": ("SEED-TRANSFER-0001", SubscriptionPlan.PREMIUM, "2500.00"),
        "services": (
            (
                "Catering para eventos",
                "catering-eventos",
                "Menú y atención para celebraciones.",
                "3500.00",
                180,
                IMAGES["burger"],
            ),
            (
                "Reserva de salón",
                "reserva-salon",
                "Un espacio preparado para tu encuentro.",
                None,
                120,
                IMAGES["coffee"],
            ),
        ),
        "categories": (
            {
                "name": "Cafés y bebidas",
                "slug": "cafes-bebidas",
                "description": "Café recién preparado para cualquier momento del día.",
                "image": IMAGES["coffee"],
                "platform_category": "cafeterias",
                "products": (
                    (
                        "Café cubano",
                        "cafe-cubano",
                        "Café intenso preparado al momento.",
                        "120.00",
                        IMAGES["coffee"],
                    ),
                    (
                        "Café latte",
                        "cafe-latte",
                        "Espresso, leche cremosa y arte latte.",
                        "260.00",
                        IMAGES["latte"],
                    ),
                ),
            },
            {
                "name": "Platos fuertes",
                "slug": "platos-fuertes",
                "description": "Favoritos abundantes para almorzar o cenar.",
                "image": IMAGES["burger"],
                "platform_category": "restaurantes",
                "products": (
                    (
                        "Hamburguesa de la casa",
                        "hamburguesa-casa",
                        "Doble carne, queso y vegetales frescos.",
                        "980.00",
                        IMAGES["burger"],
                    ),
                    (
                        "Pizza margarita",
                        "pizza-margarita",
                        "Tomate, mozzarella y albahaca sobre masa artesanal.",
                        "1100.00",
                        IMAGES["pizza"],
                    ),
                ),
            },
            {
                "name": "Comida rápida",
                "slug": "comida-rapida",
                "description": "Opciones sabrosas para comer sin demora.",
                "image": IMAGES["sandwich"],
                "platform_category": "restaurantes",
                "products": (
                    (
                        "Sándwich tostado",
                        "sandwich-tostado",
                        "Pan crujiente con relleno caliente y salsas.",
                        "520.00",
                        IMAGES["sandwich"],
                    ),
                    (
                        "Tacos mixtos",
                        "tacos-mixtos",
                        "Selección de tacos con vegetales y limón.",
                        "760.00",
                        IMAGES["tacos"],
                    ),
                ),
            },
        ),
    },
    {
        "owner_email": SECOND_OWNER_EMAIL,
        "name": "Dulce Alma",
        "slug": "dulce-alma",
        "description": (
            "Repostería artesanal para celebrar lo cotidiano y las fechas importantes. "
            "Preparamos dulces, panes y encargos con ingredientes seleccionados."
        ),
        "sells_online": True,
        "contact_phone": "+5352222222",
        "platform_category": "dulces-panaderia",
        "hero": IMAGES["cake"],
        "logo": IMAGES["cupcake"],
        "payment": ("SEED-TRANSFER-0002", SubscriptionPlan.BASIC, "1500.00"),
        "services": (),
        "categories": (
            {
                "name": "Pasteles",
                "slug": "pasteles",
                "description": "Pasteles para compartir y celebrar.",
                "image": IMAGES["cake"],
                "platform_category": "dulces-panaderia",
                "products": (
                    (
                        "Pastel de chocolate",
                        "pastel-chocolate",
                        "Bizcocho húmedo con crema y cobertura de chocolate.",
                        "1850.00",
                        IMAGES["cake"],
                    ),
                    (
                        "Pastel de cumpleaños",
                        "pastel-cumpleanos",
                        "Pastel decorado por encargo para tu celebración.",
                        "2200.00",
                        IMAGES["cake"],
                    ),
                ),
            },
            {
                "name": "Dulces individuales",
                "slug": "dulces-individuales",
                "description": "Porciones pequeñas, coloridas y listas para disfrutar.",
                "image": IMAGES["cupcake"],
                "platform_category": "dulces-panaderia",
                "products": (
                    (
                        "Cupcake de vainilla",
                        "cupcake-vainilla",
                        "Cupcake suave con crema y confeti de colores.",
                        "280.00",
                        IMAGES["cupcake"],
                    ),
                    (
                        "Croissant artesanal",
                        "croissant-artesanal",
                        "Hojaldre dorado, ligero y recién horneado.",
                        "320.00",
                        IMAGES["croissant"],
                    ),
                ),
            },
            {
                "name": "Panadería",
                "slug": "panaderia",
                "description": "Panes artesanales para la mesa de cada día.",
                "image": IMAGES["bread"],
                "platform_category": "dulces-panaderia",
                "products": (
                    (
                        "Pan rústico",
                        "pan-rustico",
                        "Hogaza artesanal de corteza firme y miga tierna.",
                        "420.00",
                        IMAGES["bread"],
                    ),
                    (
                        "Pan integral",
                        "pan-integral",
                        "Pan de granos y semillas, horneado cada mañana.",
                        "480.00",
                        IMAGES["bread"],
                    ),
                ),
            },
        ),
    },
    {
        "owner_email": OWNER_EMAIL,
        "name": "Estudio Horizonte",
        "slug": "estudio-horizonte",
        "description": (
            "Estudio creativo con impresiones, álbumes y servicios de fotografía profesional. "
            "Compra piezas listas o conversa con el equipo para preparar una sesión a tu medida."
        ),
        "sells_online": True,
        "contact_phone": "+5351111111",
        "platform_category": "cafeterias",
        "hero": IMAGES["latte"],
        "logo": IMAGES["coffee"],
        "payment": ("SEED-TRANSFER-0003", SubscriptionPlan.BASIC, "1500.00"),
        "services": (
            (
                "Sesión de retratos",
                "sesion-retratos",
                "Una experiencia fotográfica personalizada.",
                "2800.00",
                90,
                IMAGES["latte"],
            ),
        ),
        "categories": (
            {
                "name": "Impresiones y álbumes",
                "slug": "impresiones-albumes",
                "description": "Recuerdos impresos con terminación profesional.",
                "image": IMAGES["latte"],
                "platform_category": "cafeterias",
                "products": (
                    (
                        "Álbum fotográfico artesanal",
                        "album-fotografico",
                        "Álbum encuadernado con veinte páginas personalizables.",
                        "3200.00",
                        IMAGES["latte"],
                    ),
                    (
                        "Pack de impresiones premium",
                        "impresiones-premium",
                        "Diez fotografías impresas en papel profesional.",
                        "950.00",
                        IMAGES["coffee"],
                    ),
                ),
            },
        ),
    },
    {
        "owner_email": SECOND_OWNER_EMAIL,
        "name": "Próximo Bisne",
        "slug": "proximo-bisne",
        "description": "Un negocio preparando su presencia digital.",
        "sells_online": False,
        "contact_phone": "+5352222222",
        "platform_category": "dulces-panaderia",
        "hero": IMAGES["bread"],
        "logo": IMAGES["cupcake"],
        "payment": ("SEED-TRANSFER-0004", SubscriptionPlan.BASIC, "1500.00"),
        "services": (),
        "categories": (),
    },
)


async def _upsert_user(
    session: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    *,
    platform_admin: bool = False,
    legacy_email: str | None = None,
) -> UserModel:
    user = await session.scalar(select(UserModel).where(UserModel.email == email))
    if user is None and legacy_email is not None:
        user = await session.scalar(select(UserModel).where(UserModel.email == legacy_email))
        if user is not None:
            user.email = email
    if user is None:
        user = UserModel(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=True,
            is_verified=True,
            is_platform_admin=platform_admin,
        )
        session.add(user)
        await session.flush()
    else:
        user.password_hash = hash_password(password)
    user.full_name = full_name
    user.is_active = True
    user.is_verified = True
    user.is_platform_admin = platform_admin
    return user


async def _upsert_platform_categories(session: AsyncSession) -> dict[str, PlatformCategoryModel]:
    result: dict[str, PlatformCategoryModel] = {}
    for name, slug, description in PLATFORM_CATEGORIES:
        item = await session.scalar(
            select(PlatformCategoryModel).where(PlatformCategoryModel.slug == slug)
        )
        if item is None:
            item = PlatformCategoryModel(
                name=name,
                slug=slug,
                description=description,
                is_active=True,
            )
            session.add(item)
            await session.flush()
        item.name = name
        item.description = description
        item.is_active = True
        result[slug] = item
    return result


async def _upsert_business(
    session: AsyncSession,
    spec: dict[str, Any],
    owners: dict[str, UserModel],
    platform_categories: dict[str, PlatformCategoryModel],
) -> None:
    business = await session.scalar(select(BusinessModel).where(BusinessModel.slug == spec["slug"]))
    if business is None:
        business = BusinessModel(
            name=spec["name"],
            slug=spec["slug"],
            description=spec["description"],
            sells_online=spec["sells_online"],
            currency="CUP",
            timezone="America/Havana",
            contact_email=spec["owner_email"],
            contact_phone=spec["contact_phone"],
            is_published=True,
            platform_category_id=platform_categories[spec["platform_category"]].id,
        )
        session.add(business)
        await session.flush()
    business.name = spec["name"]
    business.description = spec["description"]
    business.sells_online = spec["sells_online"]
    business.currency = "CUP"
    business.timezone = "America/Havana"
    business.contact_email = spec["owner_email"]
    business.contact_phone = spec["contact_phone"]
    business.is_published = True
    business.archived_at = None
    business.platform_category_id = platform_categories[spec["platform_category"]].id

    owner = owners[spec["owner_email"]]
    membership = await session.scalar(
        select(BusinessMemberModel).where(
            BusinessMemberModel.business_id == business.id,
            BusinessMemberModel.user_id == owner.id,
        )
    )
    if membership is None:
        membership = BusinessMemberModel(business_id=business.id, user_id=owner.id)
        session.add(membership)
    membership.role = "owner"

    site = await session.scalar(
        select(BusinessSiteModel).where(BusinessSiteModel.business_id == business.id)
    )
    if site is None:
        site = BusinessSiteModel(business_id=business.id)
        session.add(site)
    site.hero_image_url = spec["hero"]
    site.logo_url = spec["logo"]

    transaction, plan, amount = spec["payment"]
    payment = await session.scalar(
        select(SubscriptionPaymentModel).where(
            SubscriptionPaymentModel.transaction_number == transaction
        )
    )
    if payment is None:
        payment = SubscriptionPaymentModel(transaction_number=transaction)
        session.add(payment)
    payment.business_id = business.id
    payment.plan = plan
    payment.phone_number = spec["contact_phone"]
    payment.execution_date = date(2026, 7, 28)
    payment.expiration_date = date(2026, 8, 28)
    payment.amount_paid = Decimal(amount)

    seeded_category_slugs = {item["slug"] for item in spec["categories"]}
    seeded_product_slugs = {
        product[1] for category in spec["categories"] for product in category["products"]
    }
    existing_products = await session.scalars(
        select(ProductModel).where(ProductModel.business_id == business.id)
    )
    for existing_product in existing_products:
        if existing_product.slug not in seeded_product_slugs:
            existing_product.is_available = False
            existing_product.is_published = False
            existing_product.archived_at = datetime.now(UTC)

    seeded_service_slugs = {service[1] for service in spec.get("services", ())}
    existing_services = await session.scalars(
        select(ServiceModel).where(ServiceModel.business_id == business.id)
    )
    for existing_service in existing_services:
        if existing_service.slug not in seeded_service_slugs:
            existing_service.is_available = False
            existing_service.is_published = False
            existing_service.archived_at = datetime.now(UTC)
    existing_categories = await session.scalars(
        select(CategoryModel).where(CategoryModel.business_id == business.id)
    )
    for existing_category in existing_categories:
        if existing_category.slug not in seeded_category_slugs:
            existing_category.is_visible = False

    for position, category_spec in enumerate(spec["categories"]):
        category = await session.scalar(
            select(CategoryModel).where(
                CategoryModel.business_id == business.id,
                CategoryModel.slug == category_spec["slug"],
            )
        )
        if category is None:
            category = CategoryModel(
                business_id=business.id,
                name=category_spec["name"],
                slug=category_spec["slug"],
                description=category_spec["description"],
                image_url=category_spec["image"],
                position=position,
                is_visible=True,
            )
            session.add(category)
            await session.flush()
        category.name = category_spec["name"]
        category.description = category_spec["description"]
        category.image_url = category_spec["image"]
        category.position = position
        category.is_visible = True

        for name, slug, description, price, image_url in category_spec["products"]:
            product = await session.scalar(
                select(ProductModel).where(
                    ProductModel.business_id == business.id,
                    ProductModel.slug == slug,
                )
            )
            if product is None:
                product = ProductModel(business_id=business.id, slug=slug)
                session.add(product)
            product.category_id = category.id
            product.platform_category_id = platform_categories[
                category_spec["platform_category"]
            ].id
            product.name = name
            product.description = description
            product.price = Decimal(price)
            product.currency = "CUP"
            product.image_url = image_url
            product.is_available = True
            product.is_published = True
            product.track_inventory = False
            product.stock_quantity = None
            product.archived_at = None

    for name, slug, description, price, duration, image_url in spec.get("services", ()):
        service = await session.scalar(
            select(ServiceModel).where(
                ServiceModel.business_id == business.id, ServiceModel.slug == slug
            )
        )
        if service is None:
            service = ServiceModel(business_id=business.id, slug=slug)
            session.add(service)
        service.platform_category_id = platform_categories[spec["platform_category"]].id
        service.name = name
        service.description = description
        service.price = Decimal(price) if price else None
        service.currency = "CUP" if price else None
        service.duration_minutes = duration
        service.image_url = image_url
        service.is_available = True
        service.is_published = True
        service.archived_at = None


async def seed() -> None:
    async with async_session_factory() as session:
        await _upsert_user(
            session,
            ADMIN_EMAIL,
            ADMIN_PASSWORD,
            "Administración El Bisne",
            platform_admin=True,
            legacy_email="admin@elbisne.local",
        )
        owners = {
            OWNER_EMAIL: await _upsert_user(
                session,
                OWNER_EMAIL,
                OWNER_PASSWORD,
                "María Pérez",
                legacy_email="owner.demo@elbisne.local",
            ),
            SECOND_OWNER_EMAIL: await _upsert_user(
                session,
                SECOND_OWNER_EMAIL,
                SECOND_OWNER_PASSWORD,
                "Laura García",
            ),
        }

        payment_settings = await session.get(PlatformPaymentSettingsModel, 1)
        if payment_settings is None:
            payment_settings = PlatformPaymentSettingsModel(id=1)
            session.add(payment_settings)
        payment_settings.bank_card = "9200123412341234"
        payment_settings.confirmation_phone_number = "+5350000000"

        for currency, value in (("CUP", "1"), ("USD", "350"), ("EUR", "390")):
            rate = await session.scalar(
                select(ExchangeRateModel).where(ExchangeRateModel.currency == currency)
            )
            if rate is None:
                rate = ExchangeRateModel(currency=currency)
                session.add(rate)
            rate.value_in_cup = Decimal(value)

        platform_categories = await _upsert_platform_categories(session)
        for business_spec in BUSINESSES:
            await _upsert_business(session, business_spec, owners, platform_categories)

        await session.commit()

    await engine.dispose()
    print("Seed completed: 4 businesses, 7 categories, 14 products and 3 services.")
    print(f"Platform admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"Demo owner: {OWNER_EMAIL} / {OWNER_PASSWORD}")
    print(f"Dulce Alma owner: {SECOND_OWNER_EMAIL} / {SECOND_OWNER_PASSWORD}")
    print(
        "Public demos: /bisne/cafe-bisne-demo, /bisne/dulce-alma, "
        "/bisne/estudio-horizonte and /bisne/proximo-bisne"
    )


if __name__ == "__main__":
    asyncio.run(seed())
