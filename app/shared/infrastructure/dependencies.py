from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory, get_db
from app.modules.analytics.application.commands.analytics import (
    TrackPublicEvent,
    TrackPublicEventHandler,
)
from app.modules.analytics.application.queries.analytics import (
    GetBusinessDashboard,
    GetBusinessDashboardHandler,
)
from app.modules.auth.application.commands.auth import (
    LoginUser,
    LoginUserHandler,
    RefreshSession,
    RefreshSessionHandler,
    RegisterUser,
    RegisterUserHandler,
)
from app.modules.auth.application.queries.users import GetCurrentUser, GetCurrentUserHandler
from app.modules.businesses.application.commands.businesses import (
    AddBusinessMember,
    AddBusinessMemberHandler,
    ArchiveBusiness,
    ArchiveBusinessHandler,
    ChangeMemberRole,
    ChangeMemberRoleHandler,
    CreateBusiness,
    CreateBusinessHandler,
    RemoveBusinessMember,
    RemoveBusinessMemberHandler,
    UpdateBusiness,
    UpdateBusinessHandler,
)
from app.modules.businesses.application.queries.businesses import (
    GetBusiness,
    GetBusinessHandler,
    ListBusinessMembers,
    ListBusinessMembersHandler,
    ListManagedBusinesses,
    ListManagedBusinessesHandler,
)
from app.modules.catalog.application.commands.catalog import (
    ArchiveProduct,
    ArchiveProductHandler,
    CreateCategory,
    CreateCategoryHandler,
    CreateProduct,
    CreateProductHandler,
    DeleteCategory,
    DeleteCategoryHandler,
    UpdateCategory,
    UpdateCategoryHandler,
    UpdateProduct,
    UpdateProductHandler,
)
from app.modules.catalog.application.queries.catalog import (
    GetProduct,
    GetProductHandler,
    GetPublicCatalog,
    GetPublicCatalogHandler,
    ListCategories,
    ListCategoriesHandler,
    ListProducts,
    ListProductsHandler,
)
from app.modules.orders.application.commands.orders import (
    ChangeOrderStatus,
    ChangeOrderStatusHandler,
    CreateGuestOrder,
    CreateGuestOrderHandler,
)
from app.modules.orders.application.queries.orders import (
    GetOrder,
    GetOrderHandler,
    ListOrders,
    ListOrdersHandler,
)
from app.modules.sites.application.queries.sites import (
    GetPublicBusiness,
    GetPublicBusinessHandler,
)
from app.shared.application.cqrs import CommandBus, QueryBus
from app.shared.application.unit_of_work import SqlAlchemyUnitOfWork


def _uow() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(async_session_factory)


async def get_command_bus() -> AsyncIterator[CommandBus]:
    bus = CommandBus()
    bus.register(RegisterUser, RegisterUserHandler(_uow()))
    bus.register(LoginUser, LoginUserHandler(_uow()))
    bus.register(RefreshSession, RefreshSessionHandler(_uow()))
    bus.register(CreateBusiness, CreateBusinessHandler(_uow()))
    bus.register(CreateCategory, CreateCategoryHandler(_uow()))
    bus.register(CreateProduct, CreateProductHandler(_uow()))
    bus.register(CreateGuestOrder, CreateGuestOrderHandler(_uow()))
    bus.register(TrackPublicEvent, TrackPublicEventHandler(_uow()))
    bus.register(UpdateBusiness, UpdateBusinessHandler(_uow()))
    bus.register(ArchiveBusiness, ArchiveBusinessHandler(_uow()))
    bus.register(AddBusinessMember, AddBusinessMemberHandler(_uow()))
    bus.register(ChangeMemberRole, ChangeMemberRoleHandler(_uow()))
    bus.register(RemoveBusinessMember, RemoveBusinessMemberHandler(_uow()))
    bus.register(UpdateCategory, UpdateCategoryHandler(_uow()))
    bus.register(DeleteCategory, DeleteCategoryHandler(_uow()))
    bus.register(UpdateProduct, UpdateProductHandler(_uow()))
    bus.register(ArchiveProduct, ArchiveProductHandler(_uow()))
    bus.register(ChangeOrderStatus, ChangeOrderStatusHandler(_uow()))
    yield bus


async def get_query_bus(
    session: AsyncSession = Depends(get_db),
) -> AsyncIterator[QueryBus]:
    bus = QueryBus()
    bus.register(GetCurrentUser, GetCurrentUserHandler(session))
    bus.register(ListManagedBusinesses, ListManagedBusinessesHandler(session))
    bus.register(GetPublicCatalog, GetPublicCatalogHandler(session))
    bus.register(GetPublicBusiness, GetPublicBusinessHandler(session))
    bus.register(GetBusinessDashboard, GetBusinessDashboardHandler(session))
    bus.register(GetBusiness, GetBusinessHandler(session))
    bus.register(ListBusinessMembers, ListBusinessMembersHandler(session))
    bus.register(ListCategories, ListCategoriesHandler(session))
    bus.register(ListProducts, ListProductsHandler(session))
    bus.register(GetProduct, GetProductHandler(session))
    bus.register(ListOrders, ListOrdersHandler(session))
    bus.register(GetOrder, GetOrderHandler(session))
    yield bus
