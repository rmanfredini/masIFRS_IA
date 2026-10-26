import json
import os
import rdflib
from datetime import datetime
from peak import Message, OneShotBehaviour


# ── Políticas globais de operação do banco de baterias ─────────────────────
# Ajuste esses limiares conforme as especificações do sistema físico.
BATTERY_MIN_SOC_PERCENT = 20.0   # SoC mínimo permitido para descarga (%)
BATTERY_MAX_SOC_PERCENT = 95.0   # SoC máximo permitido para carga (%)
BATTERY_MIN_POWER_KW    = 0.0    # Potência mínima válida (kW)


class StorageDataInformProcessor(OneShotBehaviour):
    """
    Processa a resposta StorageDataInform vinda do Meter após o
    StorageDataRequest enviado pelo ActiveRuleInformProcessor.

    Fluxo:
      1. Extrai o estado atual do banco de baterias (SoC, potência, etc.).
      2. Valida a ação da regra contra as políticas globais e o estado real.
      3a. Aprovação  → envia ActiveRuleAgree ao Coordinator.
      3b. Recusa     → envia ActiveRuleRefuse ao Coordinator.
    """

    def __init__(self, msg: Message):
        super().__init__()
        self.message = msg

    async def on_start(self):
        print("{} - [{}] - Starting StorageDataInformProcessor . . .".format(
            datetime.now(), self.agent.name))

    async def run(self):
        try:
            # ── 1. Recuperar contexto da regra pendente ──────────────────────
            pending_key = getattr(self.agent, "last_storage_request_key", None)
            pending_rules = getattr(self.agent, "pending_rules", {})

            if not pending_key or pending_key not in pending_rules:
                print(f"⚠️ [{self.agent.name}] Nenhuma regra pendente encontrada para correlacionar StorageDataInform.")
                return

            rule_ctx = pending_rules.pop(pending_key)
            coordinator_msg = rule_ctx["coordinator_msg"]
            active_rule = rule_ctx.get("active_rule", "unknown")

            print(f"🔋 [{self.agent.name}] StorageDataInform recebido do Meter.")
            print(f"   🔖 Regra em análise: {active_rule}")

            # ── 2. Parsear estado da bateria do corpo da mensagem ────────────
            storage_state = self._parse_storage_data(self.message.body)

            soc = storage_state.get("soc_percent")
            power_kw = storage_state.get("power_kw")
            action_type = storage_state.get("action_type", "unknown")

            print(f"   📊 Estado da bateria:")
            print(f"      SoC          : {soc}%")
            print(f"      Potência     : {power_kw} kW")
            print(f"      Ação da regra: {action_type}")

            # ── 3. Validar contra políticas globais ──────────────────────────
            valid, reason = self._validate_policy(soc, power_kw, action_type)

            # ── 4. Enviar resposta ao Coordinator ────────────────────────────
            if valid:
                await self._send_agree(coordinator_msg, active_rule)
                print(f"✅ [{self.agent.name}] ActiveRuleAgree enviado ao Coordinator. Motivo: {reason}")
            else:
                await self._send_refuse(coordinator_msg, active_rule, reason)
                print(f"🚫 [{self.agent.name}] ActiveRuleRefuse enviado ao Coordinator. Motivo: {reason}")

        except Exception as e:
            print(f"❌ [{self.agent.name}] Erro em StorageDataInformProcessor: {e}")
            import traceback
            traceback.print_exc()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _parse_storage_data(self, body: str) -> dict:
        """
        Tenta extrair os dados da bateria do corpo da mensagem.
        Suporta JSON (legado) e RDF/Turtle.
        Retorna dicionário com chaves: soc_percent, power_kw, action_type.
        """
        state = {
            "soc_percent": None,
            "power_kw": None,
            "action_type": "unknown",
        }

        if not body:
            return state

        # Tentativa 1: JSON simples
        try:
            data = json.loads(body)
            state["soc_percent"] = float(data.get("soc_percent", data.get("soc", 50.0)))
            state["power_kw"]    = float(data.get("power_kw", data.get("potencia_kw", 0.0)))
            state["action_type"] = data.get("action_type", "unknown")
            return state
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Tentativa 2: RDF/Turtle — extrai literais numéricos conhecidos
        try:
            CAO  = rdflib.Namespace("http://my.campus.org/communicative-acts#")
            IESO = rdflib.Namespace("https://www.gecad.isep.ipp.pt/ieso/v1.1.0/")

            g = rdflib.Graph()
            g.parse(data=body, format="turtle")

            # SoC
            for _, _, obj in g.triples((None, IESO.stateOfCharge, None)):
                try:
                    state["soc_percent"] = float(obj)
                    break
                except ValueError:
                    pass
            for _, _, obj in g.triples((None, CAO.socPercent, None)):
                try:
                    state["soc_percent"] = float(obj)
                    break
                except ValueError:
                    pass

            # Potência
            for _, _, obj in g.triples((None, IESO.activePower, None)):
                try:
                    state["power_kw"] = float(obj)
                    break
                except ValueError:
                    pass
            for _, _, obj in g.triples((None, CAO.powerKW, None)):
                try:
                    state["power_kw"] = float(obj)
                    break
                except ValueError:
                    pass

        except Exception as e:
            print(f"⚠️ [{self.agent.name}] Falha ao parsear RDF de StorageDataInform: {e}")

        # Defaults seguros quando não há dados (evita recusa por falta de informação)
        if state["soc_percent"] is None:
            print(f"⚠️ [{self.agent.name}] SoC não encontrado na mensagem — usando valor padrão 50%")
            state["soc_percent"] = 50.0
        if state["power_kw"] is None:
            print(f"⚠️ [{self.agent.name}] Potência não encontrada — usando valor padrão 0 kW")
            state["power_kw"] = 0.0

        return state

    def _validate_policy(self, soc, power_kw, action_type: str):
        """
        Valida a ação da regra contra as políticas globais.

        Regras de negócio:
          - Descarga (discharge/descarregar): proibido se SoC <= BATTERY_MIN_SOC_PERCENT
          - Carga    (charge/carregar)      : proibido se SoC >= BATTERY_MAX_SOC_PERCENT
          - Potência negativa               : sempre inválida
        """
        action_lower = action_type.lower()

        if power_kw < BATTERY_MIN_POWER_KW:
            return False, f"Potência inválida: {power_kw} kW (mínimo {BATTERY_MIN_POWER_KW} kW)"

        if any(kw in action_lower for kw in ("discharge", "descarregar", "decharge")):
            if soc is not None and soc <= BATTERY_MIN_SOC_PERCENT:
                return (
                    False,
                    f"SoC insuficiente para descarga: {soc}% ≤ {BATTERY_MIN_SOC_PERCENT}% (mínimo de segurança)"
                )

        if any(kw in action_lower for kw in ("charge", "carregar", "recharge")):
            if soc is not None and soc >= BATTERY_MAX_SOC_PERCENT:
                return (
                    False,
                    f"Bateria já está cheia: {soc}% ≥ {BATTERY_MAX_SOC_PERCENT}% (máximo de segurança)"
                )

        return True, f"Ação '{action_type}' aprovada (SoC={soc}%, P={power_kw} kW)"

    async def _send_agree(self, coordinator_msg: Message, active_rule: str):
        """Constrói e envia ActiveRuleAgree ao Coordinator."""
        body = self._build_response_body("active-rule-agree.sparql", active_rule)

        response = coordinator_msg.make_reply()
        response.set_metadata("performative", "agree")
        response.set_metadata("ontology", "cao")
        response.set_metadata("language", "turtle")
        response.thread = "active-rule-agree"
        response.body = body

        await self.send(response)

    async def _send_refuse(self, coordinator_msg: Message, active_rule: str, reason: str):
        """Constrói e envia ActiveRuleRefuse ao Coordinator."""
        body = self._build_response_body("active-rule-refuse.sparql", active_rule)

        response = coordinator_msg.make_reply()
        response.set_metadata("performative", "refuse")
        response.set_metadata("ontology", "cao")
        response.set_metadata("language", "turtle")
        response.thread = "active-rule-refuse"
        response.body = body

        print(f"   ℹ️  Razão da recusa: {reason}")
        await self.send(response)

    def _build_response_body(self, sparql_filename: str, active_rule_iri: str) -> str:
        """
        Usa o template SPARQL CONSTRUCT para gerar o corpo RDF/Turtle
        da resposta (agree ou refuse), substituindo o placeholder de IRI.
        """
        sparql_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "sparql", "construct", sparql_filename
        ))

        if not os.path.isfile(sparql_path):
            # Fallback mínimo
            rdf_type = "ActiveRuleAgree" if "agree" in sparql_filename else "ActiveRuleRefuse"
            return (
                "@prefix cao: <http://my.campus.org/communicative-acts#> .\n"
                "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
                f"_:r rdf:type cao:{rdf_type} .\n"
            )

        with open(sparql_path, "r", encoding="utf-8") as f:
            sparql_template = f.read()

        # Substituir placeholder pelo IRI real da regra
        sparql_query = sparql_template.replace("<[ACTIVE_RULE_INFORM_IRI]>", f"<{active_rule_iri}>")

        try:
            g = rdflib.Graph()
            result = g.query(sparql_query)
            for row in result:
                g.add(row)
            return g.serialize(format="turtle")
        except Exception as e:
            print(f"⚠️ [{self.agent.name}] Erro ao construir RDF de resposta ({sparql_filename}): {e}")
            return ""

    async def on_end(self):
        print("{} - [{}] - Ending StorageDataInformProcessor . . .".format(
            datetime.now(), self.agent.name))
