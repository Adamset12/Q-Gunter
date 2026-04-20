"""Función de conveniencia para ejecutar Q-Gunter."""

import logging
from pathlib import Path
from typing import Any

# Logging a fichero para debugging
DEBUG_LOG_PRIMARY = Path("/tmp/qgunter-debug.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(DEBUG_LOG_PRIMARY, mode="w"),
    ],
)
logger = logging.getLogger(__name__)


async def run_agent(
    target: str,
    custom_instruction: str | None = None,
    model: str | None = None,
    working_dir: str | None = None,
    debug: bool = False,
    resume_session: str | None = None,
) -> dict[str, Any]:
    """Ejecuta Q-Gunter contra un objetivo.

    Args:
        target: IP, URL, o dominio del objetivo
        custom_instruction: Contexto adicional para el agente
        model: Modelo de Claude (override)
        working_dir: Directorio de trabajo (override)
        debug: Modo debug
        resume_session: ID de sesión a reanudar
    """
    from qgunter.core.config import load_config
    from qgunter.core.controller import AgentController

    if debug:
        logger.info("=" * 60)
        logger.info("Q-GUNTER DEBUG MODE")
        logger.info(f"Target: {target}")
        logger.info("=" * 60)

    config_kwargs: dict[str, Any] = {"target": target}
    if custom_instruction:
        config_kwargs["custom_instruction"] = custom_instruction
    if model:
        config_kwargs["llm_model"] = model
    if working_dir:
        config_kwargs["working_directory"] = Path(working_dir)

    config = load_config(**config_kwargs)

    task = f"Solve this CTF challenge and capture the flag(s): {target}"
    if custom_instruction:
        task += f"\n\nChallenge context: {custom_instruction}"

    controller = AgentController(config)
    return await controller.run(task, resume_session_id=resume_session)