import asyncio
import uuid
from typing import Union, Mapping, Callable, Optional, Literal, Coroutine, cast
from sqlalchemy import select

from app.db.session import async_session_factory
from app.modules.auth.infrastructure.models.user import UserModel
from app.shared.infrastructure.security import hash_password

type MenuList = list[Mapping[Literal["text", "cb"], Union[str, Callable]]]
type Menu = Optional[MenuList]


async def get_admins():
    async with async_session_factory() as session:
        stmt = select(UserModel).where(UserModel.is_platform_admin.is_(True))
        return [
            dict(id=u.id, full_name=u.full_name, email=u.email)
            for u in (await session.scalars(stmt)).all()
        ]


async def create_admin():
    print("Creating a new admin user\n")
    async with async_session_factory() as session:
        email = input("Enter a valid email: ")
        user_exist = (
            await session.execute(
                select(UserModel).where(UserModel.email == (email or "null").strip())
            )
        ).first()
        if user_exist:
            return "User with this email already exists"
        name = input("Enter the full name of the user: ")
        passwd = input("Enter the password: ")
        user = UserModel(
            email=email.lower(),
            password_hash=hash_password(passwd),
            full_name=name.strip(),
            is_platform_admin=True,
        )
        session.add(user)
        await session.commit()
        print()
        return dict(id=user.id, full_name=user.full_name, email=user.email)


async def update_admin():
    print("Updating an admin user\n")
    async with async_session_factory() as session:
        user_id_raw = input("Enter a user id: ").strip()
        try:
            user_uuid = uuid.UUID(user_id_raw)
        except (ValueError, AttributeError):
            return "User with this id doesnt exist"
        user = (
            await session.scalars(select(UserModel).where(UserModel.id == user_uuid))
        ).first()
        if not user:
            return "User with this id doesnt exist"
        email = input("Enter a valid email: ").strip().lower()
        name = input("Enter the full name of the user: ").strip()
        passwd = input("Enter the password: ")
        try:
            if email:
                user.email = email
            if name:
                user.full_name = name
            if passwd:
                user.password_hash = hash_password(passwd)
            await session.commit()
            await session.refresh(user)
        except Exception as error:
            await session.rollback()
            return "Error updating user: " + str(error)

        print()
        return dict(id=user.id, full_name=user.full_name, email=user.email)


async def delete_admin():
    print("Deleting an admin user\n")
    async with async_session_factory() as session:
        user_id_raw = input("Enter a user id: ").strip()
        try:
            user_uuid = uuid.UUID(user_id_raw)
        except (ValueError, AttributeError):
            return "User with this id doesnt exist"
        user = (
            await session.scalars(select(UserModel).where(UserModel.id == user_uuid))
        ).first()
        if not user:
            return "User with this id doesnt exist"
        _pass = input("Are you sure you want to delete this user? (y/n): ")
        if _pass.lower() != "y":
            return
        await session.delete(user)
        await session.commit()
        print()
        return "User deleted"


def go_menu(i):
    global menu
    menu = {0: MAIN_MENU, 1: ADMIN_MENU}.get(i)


menu: Menu = []

ADMIN_MENU: Menu = [
    {"text": "See application admins", "cb": get_admins},
    {"text": "Create application admin", "cb": create_admin},
    {"text": "Update application admin", "cb": update_admin},
    {"text": "Delete application admin", "cb": delete_admin},
    {"text": "Main menu", "cb": lambda: go_menu(0)},
    {"text": "Exit", "cb": exit},
]

MAIN_MENU: Menu = [
    {"text": "Admin users", "cb": lambda: go_menu(1)},
    {"text": "Exit", "cb": exit},
]


def get_choice() -> int:
    for i, o in enumerate(cast(MenuList, menu)):
        print(f"{i} - {o['text']}")
    print()
    c = input("Choose an option: ")
    print()
    try:
        c = int(c)
    except:
        c = 0
    return c


async def main() -> None:
    global menu
    menu = MAIN_MENU
    while True:
        choice: int = get_choice()
        try:
            o = cast(Callable, cast(MenuList, menu)[choice]["cb"])()
            if isinstance(o, Coroutine):
                o = await o
            if o is not None:
                print(o, "\n")
                input("Press any key to continue...")
            print("\n-----------------------------------------\n")
        except Exception as error:
            print(error)
            exit()


if __name__ == "__main__":
    asyncio.run(main())
