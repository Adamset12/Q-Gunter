"""Autenticación por token compartido para el MCP Server de Manos."""

import hashlib
import hmac
import os


def verify_token(received_token: str) -> bool:
    """
    Verifica el token Bearer recibido en la cabecera Authorization.

    Usa comparación en tiempo constante (hmac.compare_digest) para
    evitar ataques de timing.
    """
    expected = os.environ.get("MANOS_TOKEN", "")
    if not expected:
        raise RuntimeError("MANOS_TOKEN no configurado en .env de Manos")
    return hmac.compare_digest(
        hashlib.sha256(received_token.encode()).digest(),
        hashlib.sha256(expected.encode()).digest(),
    )
