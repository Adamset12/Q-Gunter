"""Tests actualizados para QGunterConfig en modo distribuido.

CAMBIOS RESPECTO AL ORIGINAL:
- ELIMINADO: assert config.permission_mode == "bypassPermissions"  (campo eliminado)
- AÑADIDOS:  asserts para los nuevos campos manos_*
"""

from pathlib import Path
import pytest
from pydantic import ValidationError
from qgunter.core.config import QGunterConfig, load_config


@pytest.mark.unit
class TestConfig:
    def test_required_target(self, temp_working_dir: Path) -> None:
        with pytest.raises(ValidationError):
            QGunterConfig(working_directory=temp_working_dir)

    def test_defaults(self, temp_working_dir: Path) -> None:
        config = QGunterConfig(target="example.com", working_directory=temp_working_dir)
        assert config.llm_model == "claude-haiku-4-5-20251001"
        # permission_mode eliminado — ya no existe
        assert config.max_iterations == 300
        # Nuevos campos distribuidos
        assert config.manos_port == 7331
        assert config.manos_host == "192.168.1.100"
        assert config.manos_token == "CAMBIA_ESTE_TOKEN"

    def test_manos_url(self, temp_working_dir: Path) -> None:
        config = QGunterConfig(
            target="example.com",
            working_directory=temp_working_dir,
            manos_host="10.0.0.50",
            manos_port=8080,
        )
        assert config.manos_url == "http://10.0.0.50:8080"

    def test_load_config(self, temp_working_dir: Path) -> None:
        config = load_config(target="10.10.11.234", working_directory=temp_working_dir)
        assert config.target == "10.10.11.234"

    def test_load_config_with_manos(self, temp_working_dir: Path) -> None:
        config = load_config(
            target="10.10.11.234",
            working_directory=temp_working_dir,
            manos_host="192.168.1.200",
            manos_token="mi_token",
        )
        assert config.manos_host == "192.168.1.200"
        assert config.manos_token == "mi_token"
