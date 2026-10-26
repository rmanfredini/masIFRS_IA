"""
MAS-IFRS — Launcher (substitui ``peak start mas-ifrs.yaml``)

Uso:
    python run_mas.py                      # usa servidor XMPP já em execução (localhost:5222)
    python run_mas.py --embedded-server    # sobe o servidor XMPP embutido do SPADE (pyjabber)
    python run_mas.py --only meter predictor
    python run_mas.py --config outro.yaml

Cada agente roda em um processo próprio (como no PEAK), com o diretório do agente
no sys.path, de modo que ``from behaviour.X import ...`` continue funcionando.
"""

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def spawn_agents(cfg: dict, only: list) -> dict:
    d = cfg.get("defaults", {})
    log_folder = Path(d.get("log_folder", "logs"))
    if not log_folder.is_absolute():
        log_folder = ROOT / log_folder
    log_folder.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update({
    env.update({
        "XMPP_DOMAIN": os.getenv("XMPP_DOMAIN", str(d.get("domain", "localhost")).strip()),
        "XMPP_PORT": os.getenv("XMPP_PORT", str(d.get("port", 5222)).strip()),
        "AGENT_PASSWORD": os.getenv("AGENT_PASSWORD", str(d.get("password", "secret"))),
        "MAS_LOG_FOLDER": str(log_folder),
        "MAS_LOG_LEVEL": os.getenv("MAS_LOG_LEVEL", str(d.get("log_level", "INFO"))),
        "PYTHONPATH": str(ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
        "PYTHONUNBUFFERED": "1",
    })

    procs = {}
    for name, spec in cfg["agents"].items():
        if only and name not in only:
            continue
        script = ROOT / spec["file"]
        procs[name] = subprocess.Popen(
            [sys.executable, str(script)], cwd=str(script.parent), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,  # logs vão para <log_folder>/<agent>_main.log
        )
        print(f"▶️  {name} iniciado (pid {procs[name].pid}) — log: {log_folder / (name + '_main.log')}")
        if name == "coordinator":
            time.sleep(5)  # garante que o coordinator esteja conectado antes dos 'alive'
    return procs


def stop_agents(procs: dict) -> None:
    for name, p in procs.items():
        if p.poll() is None:
            p.send_signal(signal.SIGINT)
    deadline = time.time() + 10
    for name, p in procs.items():
        try:
            p.wait(max(0, deadline - time.time()))
        except subprocess.TimeoutExpired:
            p.kill()
    print("🏁 Todos os agentes foram encerrados.")


def main() -> None:
    parser = argparse.ArgumentParser(description="MAS-IFRS launcher (SPADE 4.1.4)")
    parser.add_argument("--config", default=str(ROOT / "mas-ifrs.yaml"))
    parser.add_argument("--only", nargs="*", default=[], help="inicia apenas os agentes informados")
    parser.add_argument("--embedded-server", action="store_true",
                        help="sobe o servidor XMPP embutido do SPADE (pyjabber)")
    args = parser.parse_args()
    cfg = load_config(Path(args.config))

    if args.embedded_server:
        import loguru
        from pyjabber.server import Server
        from pyjabber.server_parameters import Parameters

        loguru.logger.remove()  # servidor embutido silencioso

        port = int(cfg.get("defaults", {}).get("port", 5222))
        host = str(cfg.get("defaults", {}).get("domain", "localhost")).strip()

        async def run_all():
            server = Server(Parameters(host=host, client_port=port, database_in_memory=True))
            task = asyncio.create_task(server.start())
            await server.ready.wait()
            print(f"🛰️  Servidor XMPP embutido em {host}:{port}")
            procs = await asyncio.to_thread(spawn_agents, cfg, args.only)
            try:
                while any(p.poll() is None for p in procs.values()):
                    await asyncio.sleep(1)
            finally:
                stop_agents(procs)
                task.cancel()

        try:
            asyncio.run(run_all())
        except KeyboardInterrupt:
            pass
        return

    procs = spawn_agents(cfg, args.only)
    try:
        while any(p.poll() is None for p in procs.values()):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Encerrando agentes...")
    finally:
        stop_agents(procs)


if __name__ == "__main__":
    main()
