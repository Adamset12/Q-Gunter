from pathlib import Path
import pytest
from pydantic import ValidationError
from qgunter.core.config import QGunterConfig, load_config


@pytest.mark.unit
class TestConfig:
    def test_required_target(self, temp_working_dir: Path):
        with pytest.raises(ValidationError):
            QGunterConfig(working_directory=temp_working_dir)

    def test_defaults(self, temp_working_dir: Path):
        config = QGunterConfig(target="example.com", working_directory=temp_working_dir)
        assert config.llm_model == "claude-sonnet-4-5-20250929"
        assert config.permission_mode == "bypassPermissions"
        assert config.max_iterations == 300

    def test_load_config(self, temp_working_dir: Path):
        config = load_config(target="10.10.11.234", working_directory=temp_working_dir)
        assert config.target == "10.10.11.234"