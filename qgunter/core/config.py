"""Configuration management for Q-Gunter using Pydantic."""

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QGunterConfig(BaseSettings):
    """Main configuration for Q-Gunter.

    Pydantic Settings lee automáticamente variables de entorno y ficheros .env.
    Por ejemplo, si en .env pones LLM_MODEL=claude-opus-4-20250514,
    se cargará automáticamente.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === LLM ===
    llm_model: str = Field(
        default="claude-sonnet-4-5-20250929",
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
        ...,  # "..." significa OBLIGATORIO, no tiene valor por defecto
        description="Target for penetration testing (URL, IP, domain)",
    )

    custom_instruction: str | None = Field(
        default=None,
        description="Optional custom instructions for the agent",
    )

    # === Permisos ===
    permission_mode: str = Field(
        default="bypassPermissions",
        description="Permission mode for Claude Code SDK",
    )

    verbose: bool = Field(default=True)

    def __init__(self, **data: Any) -> None:
        """Inicializa y crea el directorio de trabajo si no existe."""
        super().__init__(**data)
        try:
            self.working_directory.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            if not self.working_directory.exists():
                raise


def load_config(**overrides: object) -> QGunterConfig:
    """Carga configuración desde .env + variables de entorno + overrides.

    Ejemplo:
        config = load_config(target="10.10.11.234", verbose=True)
    """
    return QGunterConfig(**overrides)