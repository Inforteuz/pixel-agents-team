"""ASGI entrypoint; deployment settings come from the service environment."""

from .app import create_app

app = create_app()
