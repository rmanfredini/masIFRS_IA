"""
MAS-IFRS — Runner SPADE 4.x
Substitui o ``peak start`` / ``peak.bootloader``: instancia um agente SPADE,
configura logging (arquivo ``<log_folder>/<agente>_main.log`` no formato lido
pelo monitor), conecta ao servidor XMPP e mantém o processo vivo.

Configuração via variáveis de ambiente (preenchidas pelo ``run_mas.py``):
  XMPP_DOMAIN     (default: localhost)
  XMPP_PORT       (default: 5222)
  AGENT_PASSWORD  (default: secret)
  MAS_LOG_FOLDER  (default: <masifrs_spade>/logs)
  MAS_LOG_LEVEL   (default: INFO)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import spade

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
ROOT_DIR = Path(__file__).resolve().parent.parent


class _StreamToLogger:
    """Redireciona print()/stdout para o logging (equivalente ao que o PEAK fazia)."""

    def __init__(self, logger: logging.Logger, level: int, original):
        self._logger = logger
        self._level = level
        self._original = original
        self._buffer = ""

    def write(self, text):
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip()
            if line:
                self._logger.log(self._level, line)
        return len(text)

    def flush(self):
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer.strip())
        self._buffer = ""

    def isatty(self):
        return False

    def __getattr__(self, item):
        return getattr(self._original, item)


def setup_logging(agent_name: str) -> None:
    level_name = os.getenv("MAS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_folder = Path(os.getenv("MAS_LOG_FOLDER", ROOT_DIR / "logs"))
    log_folder.mkdir(parents=True, exist_ok=True)

    original_stdout, original_stderr = sys.stdout, sys.stderr
    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = logging.FileHandler(log_folder / f"{agent_name}_main.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(original_stderr)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    logging.getLogger("masifrs").setLevel(level)

    # Ruído do transporte XMPP só em modo DEBUG
    noisy = logging.DEBUG if level == logging.DEBUG else logging.WARNING
    for name in ("slixmpp", "pyjabber", "aiosqlite"):
        logging.getLogger(name).setLevel(noisy)

    sys.stdout = _StreamToLogger(logging.getLogger("stdout"), logging.INFO, original_stdout)
    sys.stderr = _StreamToLogger(logging.getLogger("stderr"), logging.ERROR, original_stderr)


def run_agent(agent_cls, name: str = None) -> None:
    """Ponto de entrada de um agente: ``run_agent(meter)`` dentro de ``if __name__ == '__main__'``."""
    name = name or agent_cls.__name__
    setup_logging(name)
    log = logging.getLogger("masifrs.runner")

    domain = os.getenv("XMPP_DOMAIN", "localhost")
    port = int(os.getenv("XMPP_PORT", "5222"))
    password = os.getenv("AGENT_PASSWORD", "secret")
    # Resource "main" mantém compatibilidade com os JIDs usados nos behaviours (ex.: meter@localhost/main)
    jid = f"{name}@{domain}/main"

    async def main():
        agent = agent_cls(jid, password, port=port, verify_security=False)
        log.info("Agent starting (%s)", jid)
        await agent.start(auto_register=True)
        await spade.wait_until_finished(agent)
        log.info("Agent terminated (SPADE terminated)")

    try:
        spade.run(main())
    except KeyboardInterrupt:
        log.info("SPADE terminated (KeyboardInterrupt)")
