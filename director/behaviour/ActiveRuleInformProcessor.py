import json
import os
import rdflib
from datetime import datetime
from peak import Message, OneShotBehaviour


class ActiveRuleInformProcessor(OneShotBehaviour):
    """
    Processa a notificação ActiveRuleInform enviada pelo Coordinator.

    Fluxo:
      1. Extrai os dados da regra ativa do corpo RDF/Turtle da mensagem.
      2. Guarda a mensagem original (para poder responder ao Coordinator depois).
      3. Envia StorageDataRequest ao agente Meter para obter o estado em
         tempo real do banco de baterias.
    """

    def __init__(self, msg: Message):
        super().__init__()
        self.message = msg

    async def on_start(self):
        print("{} - [{}] - Starting ActiveRuleInformProcessor . . .".format(
            datetime.now(), self.agent.name))

    async def run(self):
        try:
            # ── 1. Parsear corpo RDF/Turtle ──────────────────────────────────
            select_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "sparql", "select",
                "get-active-rule-inform-data.sparql"
            ))

            if not os.path.isfile(select_path):
                print(f"❌ [{self.agent.name}] Arquivo SPARQL não encontrado: {select_path}")
                return

            with open(select_path, "r", encoding="utf-8") as f:
                sparql_query = f.read()

            graph = rdflib.Graph()
            graph.parse(data=self.message.body, format="turtle")
            results = graph.query(sparql_query)

            rule_data = None
            if len(results) >= 1:
                binding = results.bindings[0]
                dict_var = results.vars[0]
                raw = binding.get(dict_var)
                if raw:
                    rule_data = json.loads(str(raw))

            if not rule_data:
                print(f"⚠️ [{self.agent.name}] Não foi possível extrair dados da ActiveRuleInform.")
                return

            active_rule = rule_data.get("active_rule", "unknown")
            timestamp = rule_data.get("timestamp", datetime.now().isoformat())

            print(f"📩 [{self.agent.name}] ActiveRuleInform recebido:")
            print(f"   🔖 Regra ativa : {active_rule}")
            print(f"   🕐 Timestamp   : {timestamp}")

            # ── 2. Persistir contexto no agente para ser usado pelo StorageDataInformProcessor ──
            if not hasattr(self.agent, "pending_rules"):
                self.agent.pending_rules = {}

            # A chave é o thread de resposta único do request de storage
            storage_thread = f"storage-data-request-{self.agent.name}-{int(datetime.now().timestamp())}"

            self.agent.pending_rules[storage_thread] = {
                "coordinator_msg": self.message,   # msg original para make_reply
                "active_rule": active_rule,
                "timestamp": timestamp,
            }

            # ── 3. Enviar StorageDataRequest ao Meter ────────────────────────
            construct_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "..", "coordinator",
                "sparql", "construct", "storage-data-request.sparql"
            ))

            # Monta o corpo da mensagem via SPARQL CONSTRUCT (igual ao coordinator)
            body_content = ""
            if os.path.isfile(construct_path):
                g = rdflib.Graph()
                with open(construct_path, "r", encoding="utf-8") as f:
                    sparql_construct = f.read()
                result = g.query(sparql_construct)
                for row in result:
                    g.add(row)
                body_content = g.serialize(format="turtle")
            else:
                # Fallback: corpo mínimo
                body_content = (
                    "@prefix cao: <http://my.campus.org/communicative-acts#> .\n"
                    "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n"
                    "_:req rdf:type cao:StorageDataRequest .\n"
                )

            meter_jid = f"meter@{self.agent.jid.domain}"
            storage_req = Message(to=meter_jid)
            storage_req.set_metadata("performative", "request")
            storage_req.set_metadata("ontology", "cao")
            storage_req.set_metadata("language", "turtle")
            storage_req.thread = "storage-data-request"
            storage_req.body = body_content

            # Guardar o thread key para o processor conseguir correlacionar a resposta
            # O meter responde com thread "storage-data-inform"; usamos o campo
            # 'reply_to_thread' para correlacionar via agent state.
            self.agent.pending_rules[storage_thread]["storage_thread"] = storage_thread
            # Usar um campo simples de "último request pendente" para correlação
            self.agent.last_storage_request_key = storage_thread

            await self.send(storage_req)
            print(f"📤 [{self.agent.name}] StorageDataRequest enviado ao Meter ({meter_jid})")

        except Exception as e:
            print(f"❌ [{self.agent.name}] Erro em ActiveRuleInformProcessor: {e}")
            import traceback
            traceback.print_exc()

    async def on_end(self):
        print("{} - [{}] - Ending ActiveRuleInformProcessor . . .".format(
            datetime.now(), self.agent.name))
