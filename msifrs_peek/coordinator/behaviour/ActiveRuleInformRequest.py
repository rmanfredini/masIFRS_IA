import os
import rdflib
from datetime import datetime
from peak import Message, OneShotBehaviour


class ActiveRuleInformRequest(OneShotBehaviour):
    """
    Comportamento do Coordinator que notifica o Director quando uma regra
    é disparada (ActiveRuleInform).

    Parâmetros:
        rule_iri   : IRI da regra que foi ativada (str)
        action_type: tipo de ação identificada (ex: 'discharge', 'charge')
    """

    def __init__(self, rule_iri: str, action_type: str = "unknown"):
        super().__init__()
        self.rule_iri = rule_iri
        self.action_type = action_type

    async def on_start(self):
        print("{} - [{}] - Starting ActiveRuleInformRequest . . .".format(
            datetime.now(), self.agent.name))

    async def run(self):
        try:
            # Construir corpo RDF/Turtle da mensagem ActiveRuleInform
            body = self._build_active_rule_inform_body()

            director_jid = f"director@{self.agent.jid.domain}"
            msg = Message(to=director_jid)
            msg.set_metadata("performative", "inform")
            msg.set_metadata("ontology", "cao")
            msg.set_metadata("language", "turtle")
            msg.thread = "active-rule-inform"
            msg.body = body

            await self.send(msg)
            print(f"📤 [{self.agent.name}] ActiveRuleInform enviado ao Director:")
            print(f"   🔖 Regra: {self.rule_iri}")
            print(f"   🔧 Ação : {self.action_type}")

        except Exception as e:
            print(f"❌ [{self.agent.name}] Erro em ActiveRuleInformRequest: {e}")
            import traceback
            traceback.print_exc()

    def _build_active_rule_inform_body(self) -> str:
        """
        Gera o corpo RDF/Turtle para ActiveRuleInform usando o template SPARQL
        CONSTRUCT do coordinator (se disponível), ou um corpo mínimo.
        """
        # Tentar usar template SPARQL existente no coordinator/sparql/construct/
        sparql_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "sparql", "construct",
            "active-rule-inform.sparql"
        ))

        if os.path.isfile(sparql_path):
            with open(sparql_path, "r", encoding="utf-8") as f:
                template = f.read()
            sparql_query = (
                template
                .replace("<[RULE_IRI]>", f"<{self.rule_iri}>")
                .replace("<[ACTION_TYPE]>", self.action_type)
                .replace("<[MEASUREMENT_DATETIME]>", datetime.now().isoformat())
            )
            try:
                g = rdflib.Graph()
                result = g.query(sparql_query)
                for row in result:
                    g.add(row)
                return g.serialize(format="turtle")
            except Exception as e:
                print(f"⚠️ [{self.agent.name}] Erro ao construir ActiveRuleInform via SPARQL: {e}")

        # Fallback: corpo RDF mínimo compatível com o SELECT do Director
        cao  = "http://my.campus.org/communicative-acts#"
        time = "http://www.w3.org/2006/time#"
        rdf  = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        now  = datetime.now().isoformat()
        body = (
            f"@prefix cao:  <{cao}> .\n"
            f"@prefix time: <{time}> .\n"
            f"@prefix rdf:  <{rdf}> .\n"
            f"@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .\n\n"
            f"_:inform rdf:type cao:ActiveRuleInform ;\n"
            f"         cao:activeRule <{self.rule_iri}> ;\n"
            f"         time:hasTime _:t .\n"
            f"_:t rdf:type time:Instant ;\n"
            f"    time:inXSDDateTimeStamp \"{now}\"^^xsd:dateTime .\n"
        )
        return body

    async def on_end(self):
        print("{} - [{}] - Ending ActiveRuleInformRequest . . .".format(
            datetime.now(), self.agent.name))
