from dataclasses import dataclass

import pytest

from app.shared.application.cqrs import CommandBus, HandlerNotRegisteredError


@dataclass(frozen=True)
class ExampleCommand:
    value: int


@pytest.mark.asyncio
async def test_bus_dispatches_to_registered_handler() -> None:
    bus = CommandBus()

    async def handler(command: ExampleCommand) -> int:
        return command.value * 2

    bus.register(ExampleCommand, handler)

    assert await bus.dispatch(ExampleCommand(4)) == 8


@pytest.mark.asyncio
async def test_bus_rejects_unregistered_messages() -> None:
    with pytest.raises(HandlerNotRegisteredError):
        await CommandBus().dispatch(ExampleCommand(1))
