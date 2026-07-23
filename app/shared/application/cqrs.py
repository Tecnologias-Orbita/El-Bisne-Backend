from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.shared.domain.exceptions import ApplicationError

MessageT = TypeVar("MessageT")
ResultT = TypeVar("ResultT")
Handler = Callable[[Any], Awaitable[Any]]


class HandlerNotRegisteredError(ApplicationError):
    code = "handler_not_registered"


class MessageBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Any], Handler] = {}

    def register(self, message_type: type[MessageT], handler: Handler) -> None:
        if message_type in self._handlers:
            raise ValueError(f"Handler already registered for {message_type.__name__}")
        self._handlers[message_type] = handler

    async def dispatch(self, message: MessageT) -> Any:
        handler = self._handlers.get(type(message))
        if handler is None:
            raise HandlerNotRegisteredError(f"No handler registered for {type(message).__name__}")
        return await handler(message)


class CommandBus(MessageBus):
    pass


class QueryBus(MessageBus):
    pass
