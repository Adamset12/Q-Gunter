"""Configuration management for Q-Gunter — modo distribuido."""

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QGunterConfig(BaseSettings):
    """Configuración principal de Q-Gunter.

    Lee automáticamente desde .env y variables de entorno.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === LLM ===
    llm_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Claude model to use",
    )

    # === Agente ===
    max_iterations: int = Field(default=300, description="Maximum agent iterations")

    working_directory: Path = Field(
        default_factory=lambda: Path.cwd() / "workspace",
        description="Working directory for agent operations",
    )

    # === Objetivo ===
    target: str = Field(
        ...,
        description="Target for penetration testing (URL, IP, domain)",
    )

    custom_instruction: str | None = Field(
        default=None,
        description="Optional custom instructions for the agent",
    )

    # === Manos: MCP Server remoto ===
    # ELIMINADO: permission_mode (ya no se usa ClaudeCodeBackend local)
    manos_host: str = Field(
        default="192.168.1.100",
        description="IP de la máquina Manos en la LAN",
    )
    manos_port: int = Field(
        default=7331,
        description="Puerto HTTP del MCP Server en Manos",
    )
    manos_token: str = Field(
        default="CAMBIA_ESTE_TOKEN",
        description="Token de autenticación compartido con Manos",
    )

    verbose: bool = Field(default=True)

    @property
    def manos_url(self) -> str:
        """URL base del MCP Server de Manos."""
        return f"http://{self.manos_host}:{self.manos_port}"

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        try:
            self.working_directory.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            if not self.working_directory.exists():
                raise


def load_config(**overrides: object) -> QGunterConfig:
    """Carga configuración desde .env + entorno + overrides."""
    return QGunterConfig(**overrides)
