"""Collection of built-in pipelet templates provided by the platform."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from . import filter as builtin_filter
from . import http_webhook, logger, mqtt_publish, router, template, transformer


@dataclass(frozen=True)
class BuiltinPipelet:
    """Metadata describing a built-in pipelet template."""

    name: str
    event: str
    code: str
    description: str


def _normalize(code: str) -> str:
    """Normalise code blocks to keep indentation consistent."""

    stripped = code.strip("\n")
    return f"{stripped}\n"


_BUILTINS: list[BuiltinPipelet] = [
    BuiltinPipelet(
        name=template.DEFAULT_NAME,
        event=template.DEFAULT_EVENT,
        code=_normalize(template.CODE),
        description=template.DESCRIPTION,
    ),
    BuiltinPipelet(
        name=transformer.DEFAULT_NAME,
        event=transformer.DEFAULT_EVENT,
        code=_normalize(transformer.CODE),
        description=transformer.DESCRIPTION,
    ),
    BuiltinPipelet(
        name=builtin_filter.DEFAULT_NAME,
        event=builtin_filter.DEFAULT_EVENT,
        code=_normalize(builtin_filter.CODE),
        description=builtin_filter.DESCRIPTION,
    ),
    BuiltinPipelet(
        name=router.DEFAULT_NAME,
        event=router.DEFAULT_EVENT,
        code=_normalize(router.CODE),
        description=router.DESCRIPTION,
    ),
    BuiltinPipelet(
        name=http_webhook.DEFAULT_NAME,
        event=http_webhook.DEFAULT_EVENT,
        code=_normalize(http_webhook.CODE),
        description=http_webhook.DESCRIPTION,
    ),
    BuiltinPipelet(
        name=mqtt_publish.DEFAULT_NAME,
        event=mqtt_publish.DEFAULT_EVENT,
        code=_normalize(mqtt_publish.CODE),
        description=mqtt_publish.DESCRIPTION,
    ),
    BuiltinPipelet(
        name=logger.DEFAULT_NAME,
        event=logger.DEFAULT_EVENT,
        code=_normalize(logger.CODE),
        description=logger.DESCRIPTION,
    ),
]


def get_builtin_pipelets() -> list[BuiltinPipelet]:
    """Return a copy of the available built-in pipelet templates."""

    return list(_BUILTINS)


def iter_builtin_pipelets() -> Iterable[BuiltinPipelet]:
    """Yield the registered built-in pipelets."""

    yield from _BUILTINS


def find_builtin(name: str) -> BuiltinPipelet | None:
    """Return a built-in pipelet by name, if available."""

    for builtin in _BUILTINS:
        if builtin.name == name:
            return builtin
    return None
