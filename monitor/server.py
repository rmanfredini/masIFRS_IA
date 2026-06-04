"""
MAS-IFRS Agent Monitor — Backend Server
Serve a interface de monitoramento em tempo real dos agentes do sistema multi-agente.
"""

import os
import re
import json
import glob
import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ─── Caminhos ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
TMP_LOGS = Path("/tmp/mas-ifrs-logs")

# Agentes definidos no mas-ifrs.yaml
KNOWN_AGENTS = {
    "coordinator": {
        "label": "Coordinator",
        "icon": "🧠",
        "color": "#6366f1",
        "role": "Orquestrador central do MAS",
    },
    "meter": {
        "label": "Meter",
        "icon": "⚡",
        "color": "#f59e0b",
        "role": "Coleta dados de consumo e geração",
    },
    "predictor": {
        "label": "Predictor",
        "icon": "🔮",
        "color": "#10b981",
        "role": "Previsão de consumo e geração",
    },
    "actuator": {
        "label": "Actuator",
        "icon": "🤖",
        "color": "#ef4444",
        "role": "Executa ações de controle",
    },
    "director": {
        "label": "Director",
        "icon": "📋",
        "color": "#8b5cf6",
        "role": "Gerencia políticas do campus",
    },
}

# ─── Regex para parse de logs ───────────────────────────────────────────────────
LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)"
    r"\s*-\s*(?P<module>[^\s]+)"
    r"\s*-\s*(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)"
    r"\s*-\s*(?P<message>.+)$"
)

EMOJI_MAP = {
    "✅": "success",
    "❌": "error",
    "⚠️": "warning",
    "📤": "send",
    "💓": "heartbeat",
    "▶️": "start",
    "🏁": "end",
    "🎉": "milestone",
    "📊": "data",
    "📈": "forecast",
    "🔄": "process",
    "💾": "store",
}

app = FastAPI(title="MAS-IFRS Monitor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ────────────────────────────────────────────────────────────────────

def detect_log_level_from_message(msg: str) -> str:
    """Infere nível de log de mensagens com emoji (stdout capturado)."""
    if any(e in msg for e in ["❌", "ERRO", "Error", "error", "FALHA", "TIMEOUT"]):
        return "ERROR"
    if any(e in msg for e in ["⚠️", "WARNING", "Aviso", "ainda aguardando"]):
        return "WARNING"
    if any(e in msg for e in ["✅", "🎉", "SUCCESS", "SUCESSO", "operacional"]):
        return "SUCCESS"
    if any(e in msg for e in ["💓", "alive"]):
        return "HEARTBEAT"
    if any(e in msg for e in ["📤", "📊", "📈", "💾"]):
        return "DATA"
    return "INFO"


def resolve_sparql_query(direction: str, sender: str, receiver: str, thread: str) -> dict:
    """Tenta localizar no disco as queries SPARQL associadas a esta troca de mensagens."""
    # Limpar JIDs (ex: meter@localhost/main -> meter)
    sender_clean = sender.split("@")[0].lower()
    receiver_clean = receiver.split("@")[0].lower()
    
    construct_query = None
    construct_file = None
    select_query = None
    select_file = None
    
    # 1. Localizar a query de CONSTRUCT no agente remetente
    construct_filename = f"{thread}.sparql"
    possible_construct_paths = [
        BASE_DIR / sender_clean / "sparql" / "construct" / construct_filename,
        BASE_DIR / sender_clean / "sparql" / "construct" / construct_filename.replace("-inform", "").replace("-request", ""),
    ]
    
    for path in possible_construct_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    construct_query = fh.read()
                construct_file = str(path.relative_to(BASE_DIR))
                break
            except Exception:
                pass
                
    # 2. Localizar a query de SELECT no agente destinatário
    possible_select_filenames = [
        f"get-{thread}-data.sparql",
        f"get-{thread}-inform-data.sparql",
        f"get-{thread}-request-data.sparql",
        f"get-{thread}.sparql",
        f"get-{thread.replace('-inform', '').replace('-request', '')}-data.sparql"
    ]
    
    possible_select_paths = []
    for fn in possible_select_filenames:
        possible_select_paths.append(BASE_DIR / receiver_clean / "sparql" / "select" / fn)
        
    for path in possible_select_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    select_query = fh.read()
                select_file = str(path.relative_to(BASE_DIR))
                break
            except Exception:
                pass
                
    return {
        "construct_file": construct_file,
        "construct_query": construct_query,
        "select_file": select_file,
        "select_query": select_query
    }


def parse_log_line(line: str) -> dict | None:
    """Faz parse de uma linha de log, incluindo mensagens semânticas de agentes."""
    line = line.strip()
    if not line:
        return None

    # Formato padrão de log Python
    m = LOG_PATTERN.match(line)
    if m:
        ts_str = m.group("timestamp").replace(",", ".")
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            ts = datetime.now()

        msg_content = m.group("message")
        
        # Interceptar mensagens semânticas
        if "[SEMANTIC_MSG]" in msg_content:
            try:
                # Exemplo: [SEMANTIC_MSG] SEND | From: X | To: Y | Thread: T | Ontology: O | Performative: P | Body: B
                parts = msg_content.split(" | ")
                semantic_data = {
                    "timestamp": ts.isoformat(),
                    "module": m.group("module"),
                    "level": "SEMANTIC",
                    "is_semantic": True,
                }
                
                # Vamos reconstruir caso o Body contenha caracteres " | "
                body_part_idx = -1
                for idx, part in enumerate(parts):
                    if part.startswith("Body: "):
                        body_part_idx = idx
                        break
                
                # Fazer o parse das partes regulares
                for idx, part in enumerate(parts):
                    if body_part_idx != -1 and idx >= body_part_idx:
                        continue
                        
                    if part.startswith("[SEMANTIC_MSG] "):
                        semantic_data["direction"] = part.replace("[SEMANTIC_MSG] ", "").strip()
                    elif part.startswith("From: "):
                        semantic_data["sender"] = part.replace("From: ", "").strip()
                    elif part.startswith("To: "):
                        semantic_data["receiver"] = part.replace("To: ", "").strip()
                    elif part.startswith("Thread: "):
                        semantic_data["thread"] = part.replace("Thread: ", "").strip()
                    elif part.startswith("Ontology: "):
                        semantic_data["ontology"] = part.replace("Ontology: ", "").strip()
                    elif part.startswith("Performative: "):
                        semantic_data["performative"] = part.replace("Performative: ", "").strip()
                
                # Extrair e remontar o Body
                if body_part_idx != -1:
                    body_combined = " | ".join(parts[body_part_idx:])
                    body_escaped = body_combined.replace("Body: ", "", 1).strip()
                    semantic_data["body"] = body_escaped.replace(" [NL] ", "\n")
                else:
                    semantic_data["body"] = ""
                
                # Resolver queries SPARQL associadas
                sparql_info = resolve_sparql_query(
                    semantic_data.get("direction", ""),
                    semantic_data.get("sender", ""),
                    semantic_data.get("receiver", ""),
                    semantic_data.get("thread", "")
                )
                semantic_data.update(sparql_info)
                
                # Determinar o rótulo de exibição rápida
                dir_arrow = "➔" if semantic_data.get("direction") == "SEND" else "➔"
                sender_short = semantic_data.get("sender", "").split("@")[0]
                receiver_short = semantic_data.get("receiver", "").split("@")[0]
                
                semantic_data["message"] = (
                    f"[{semantic_data.get('direction')}] {sender_short} {dir_arrow} {receiver_short} "
                    f"({semantic_data.get('thread')}) Ontologia: {semantic_data.get('ontology')}"
                )
                
                return semantic_data
                
            except Exception as e:
                # Fallback em caso de falha no parse semântico
                return {
                    "timestamp": ts.isoformat(),
                    "module": m.group("module"),
                    "level": m.group("level"),
                    "message": f"[Falha Parse Semântico] {msg_content} | Erro: {e}",
                }

        elif "[DB_MSG]" in msg_content:
            try:
                parts = msg_content.split(" | ")
                db_data = {
                    "timestamp": ts.isoformat(),
                    "module": m.group("module"),
                    "level": "DATABASE",
                    "is_database": True,
                }
                
                for part in parts:
                    if part.startswith("[DB_MSG] "):
                        db_data["db_type"] = part.replace("[DB_MSG] ", "").strip()
                    elif part.startswith("Query: "):
                        db_data["query"] = part.replace("Query: ", "", 1).strip().replace(" [NL] ", "\n")
                    elif part.startswith("Params: "):
                        db_data["params"] = part.replace("Params: ", "", 1).strip()
                    elif part.startswith("Status: "):
                        db_data["status"] = part.replace("Status: ", "", 1).strip()
                    elif part.startswith("Result: "):
                        db_data["result"] = part.replace("Result: ", "", 1).strip().replace(" [NL] ", "\n")
                    elif part.startswith("URL: "):
                        db_data["url"] = part.replace("URL: ", "", 1).strip()
                    elif part.startswith("Action: "):
                        db_data["action"] = part.replace("Action: ", "", 1).strip()
                
                db_type = db_data.get("db_type", "DB")
                action = db_data.get("action", "")
                status = db_data.get("status", "")
                status_icon = "🟢" if status == "SUCCESS" else "🔴"
                
                if db_type == "PGSQL":
                    if action:
                        db_data["message"] = f"{status_icon} [PostgreSQL] {action} — {status}"
                    else:
                        q_snippet = db_data.get("query", "")
                        q_snippet = q_snippet.split("\n")[0][:60]
                        db_data["message"] = f"{status_icon} [PostgreSQL] Query: {q_snippet}..."
                elif db_type == "GRAPHDB":
                    act = action if action else "QUERY"
                    db_data["message"] = f"{status_icon} [GraphDB] {act} — {status}"
                else:
                    db_data["message"] = f"{status_icon} [{db_type}] Interaction"
                
                return db_data
            except Exception as e:
                return {
                    "timestamp": ts.isoformat(),
                    "module": m.group("module"),
                    "level": m.group("level"),
                    "message": f"[Falha Parse DB] {msg_content} | Erro: {e}",
                }

        return {
            "timestamp": ts.isoformat(),
            "module": m.group("module"),
            "level": m.group("level"),
            "message": msg_content,
        }

    # Linha de stdout capturada (com emojis)
    return {
        "timestamp": datetime.now().isoformat(),
        "module": "stdout",
        "level": detect_log_level_from_message(line),
        "message": line,
    }


def get_log_files() -> dict[str, Path]:
    """Retorna todos os arquivos de log disponíveis."""
    files: dict[str, Path] = {}

    for log_dir in [LOGS_DIR, TMP_LOGS]:
        if log_dir.exists():
            for f in log_dir.glob("*.log"):
                agent_name = f.stem.replace("_main", "").replace("coordenador", "coordinator")
                files[agent_name] = f

    return files


def read_log_tail(path: Path, n: int = 200) -> list[dict]:
    """Lê as últimas n linhas de um arquivo de log."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        entries = []
        for line in lines[-n:]:
            parsed = parse_log_line(line)
            if parsed:
                entries.append(parsed)
        return entries
    except Exception as e:
        return [{"timestamp": datetime.now().isoformat(), "level": "ERROR", "message": str(e), "module": "monitor"}]


def get_agent_status_from_logs(agent: str) -> dict:
    """Determina o status atual do agente a partir dos seus logs."""
    log_files = get_log_files()
    path = log_files.get(agent)

    if not path or not path.exists():
        return {"status": "unknown", "last_seen": None, "last_event": None}

    entries = read_log_tail(path, 50)
    if not entries:
        return {"status": "unknown", "last_seen": None, "last_event": None}

    last = entries[-1]
    last_seen = last.get("timestamp")
    last_msg = last.get("message", "")

    # Determinar status
    if any(k in last_msg for k in ["terminated", "terminado", "KeyboardInterrupt", "PEAK terminated"]):
        status = "offline"
    elif any(k in last_msg for k in ["operacional", "Hello!", "alive", "✅", "💓"]):
        status = "online"
    elif any(k in last_msg for k in ["❌", "ERRO", "Error", "CRITICAL"]):
        status = "error"
    elif path.exists():
        # Se o arquivo existe e foi modificado recentemente, considera em execução
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        age_secs = (datetime.now() - mtime).total_seconds()
        status = "online" if age_secs < 300 else "idle"
    else:
        status = "unknown"

    return {
        "status": status,
        "last_seen": last_seen,
        "last_event": last_msg[:120],
    }


# ─── Endpoints de dados ─────────────────────────────────────────────────────────

@app.get("/api/agents")
async def list_agents():
    """Lista todos os agentes com status atual."""
    result = []
    for agent_id, meta in KNOWN_AGENTS.items():
        status_info = get_agent_status_from_logs(agent_id)
        log_files = get_log_files()
        has_log = agent_id in log_files and log_files[agent_id].exists()

        result.append({
            "id": agent_id,
            **meta,
            **status_info,
            "has_log": has_log,
            "log_path": str(log_files.get(agent_id, "")),
        })
    return result


@app.get("/api/logs/{agent_id}")
async def get_agent_logs(agent_id: str, lines: int = 200):
    """Retorna os últimos N logs de um agente."""
    log_files = get_log_files()
    if agent_id not in log_files:
        return {"entries": [], "error": f"Nenhum arquivo de log encontrado para '{agent_id}'"}

    entries = read_log_tail(log_files[agent_id], lines)
    for e in entries:
        e["agent"] = agent_id
    return {"agent": agent_id, "entries": entries, "total": len(entries)}


@app.get("/api/logs")
async def get_all_logs(lines: int = 100):
    """Retorna logs de todos os agentes mesclados e ordenados por timestamp."""
    log_files = get_log_files()
    all_entries = []

    for agent_id, path in log_files.items():
        entries = read_log_tail(path, lines)
        for e in entries:
            e["agent"] = agent_id
            all_entries.append(e)

    all_entries.sort(key=lambda x: x.get("timestamp", ""))
    return {"entries": all_entries[-lines:]}


@app.get("/api/stats")
async def get_stats():
    """Retorna estatísticas gerais do sistema."""
    log_files = get_log_files()
    agents_online = 0
    agents_error = 0
    total_log_lines = 0

    for agent_id in KNOWN_AGENTS:
        status = get_agent_status_from_logs(agent_id)
        if status["status"] == "online":
            agents_online += 1
        elif status["status"] == "error":
            agents_error += 1

        path = log_files.get(agent_id)
        if path and path.exists():
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    total_log_lines += sum(1 for _ in fh)
            except Exception:
                pass

    return {
        "timestamp": datetime.now().isoformat(),
        "agents_total": len(KNOWN_AGENTS),
        "agents_online": agents_online,
        "agents_error": agents_error,
        "agents_idle": len(KNOWN_AGENTS) - agents_online - agents_error,
        "total_log_lines": total_log_lines,
        "log_files_found": len(log_files),
    }


# ─── SSE: Streaming de logs em tempo real ───────────────────────────────────────

async def sse_log_stream(agent_id: str | None = None) -> AsyncGenerator[str, None]:
    """Gera eventos SSE com novos logs conforme surgem."""
    log_files = get_log_files()

    # Estado inicial: posição de leitura em cada arquivo
    file_positions: dict[str, int] = {}
    targets = {agent_id: log_files[agent_id]} if agent_id and agent_id in log_files else log_files

    for ag, path in targets.items():
        if path.exists():
            file_positions[ag] = path.stat().st_size
        else:
            file_positions[ag] = 0

    # Enviar heartbeat inicial
    yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.now().isoformat()})}\n\n"

    while True:
        await asyncio.sleep(1)

        # Re-detectar arquivos (novos logs podem surgir)
        current_files = get_log_files()
        targets_now = {agent_id: current_files[agent_id]} if agent_id and agent_id in current_files else current_files

        for ag, path in targets_now.items():
            if not path.exists():
                continue

            current_size = path.stat().st_size
            last_pos = file_positions.get(ag, 0)

            if current_size > last_pos:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        fh.seek(last_pos)
                        new_content = fh.read()
                    file_positions[ag] = current_size

                    for line in new_content.splitlines():
                        parsed = parse_log_line(line)
                        if parsed:
                            parsed["agent"] = ag
                            parsed["type"] = "log"
                            yield f"data: {json.dumps(parsed)}\n\n"
                except Exception as e:
                    err = {"type": "error", "message": str(e), "agent": ag}
                    yield f"data: {json.dumps(err)}\n\n"

        # Heartbeat a cada ciclo
        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"


@app.get("/api/stream")
async def stream_all_logs(request: Request):
    """SSE endpoint — todos os agentes."""
    return StreamingResponse(
        sse_log_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/stream/{agent_id}")
async def stream_agent_logs(agent_id: str, request: Request):
    """SSE endpoint — agente específico."""
    return StreamingResponse(
        sse_log_stream(agent_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Frontend ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve a interface HTML principal."""
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>index.html não encontrado em monitor/</h1>", status_code=404)


# ─── Entrypoint ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765, reload=True)
