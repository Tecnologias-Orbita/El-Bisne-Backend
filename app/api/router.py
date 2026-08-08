from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.modules.analytics.api.routes import router as analytics_router
from app.modules.auth.api.routes import router as auth_router
from app.modules.billing.api.routes import admin_router as billing_admin_router
from app.modules.billing.api.routes import business_router as billing_business_router
from app.modules.billing.api.routes import public_router as billing_public_router
from app.modules.businesses.api.routes import router as businesses_router
from app.modules.catalog.api.routes import admin_router as catalog_admin_router
from app.modules.catalog.api.routes import public_router as catalog_public_router
from app.modules.images.api.routes import router as images_router
from app.modules.orders.api.routes import admin_router as orders_admin_router
from app.modules.orders.api.routes import router as orders_router
from app.modules.platform_categories.api.routes import (
    admin_router as platform_categories_admin_router,
)
from app.modules.platform_categories.api.routes import router as platform_categories_router
from app.modules.services.api.routes import admin_router as services_admin_router
from app.modules.services.api.routes import public_router as services_public_router
from app.modules.sites.api.routes import public_router as sites_public_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(billing_public_router)
api_router.include_router(billing_business_router)
api_router.include_router(billing_admin_router)
api_router.include_router(platform_categories_router)
api_router.include_router(platform_categories_admin_router)
api_router.include_router(businesses_router)
api_router.include_router(catalog_admin_router)
api_router.include_router(catalog_public_router)
api_router.include_router(services_admin_router)
api_router.include_router(services_public_router)
api_router.include_router(orders_router)
api_router.include_router(sites_public_router)
api_router.include_router(analytics_router)
api_router.include_router(orders_admin_router)
api_router.include_router(images_router)
