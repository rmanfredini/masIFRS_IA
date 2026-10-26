import asyncio
import json

from spade.behaviour import OneShotBehaviour
from spade.message import Message


class NotifyAlive(OneShotBehaviour):
    """
    Notifica o agente coordinator de que este agente está online.
    Substitui o antigo ``await self.client.send(alive_msg.prepare())`` do PEAK
    (SPADE 4 envia mensagens exclusivamente através de behaviours).
    """

    def __init__(self, target: str = "coordinator", delay: float = 2.0):
        super().__init__()
        self.target = target
        self.delay = delay

    async def run(self):
        try:
            # Pequena espera para garantir que a conexão XMPP esteja estabelecida
            await asyncio.sleep(self.delay)
            agent_name = self.agent.name
            target_jid = f"{self.target}@{self.agent.jid.domain}"

            msg = Message(to=target_jid)
            msg.set_metadata("performative", "inform")
            msg.thread = "agent-alive-notification"
            msg.body = json.dumps({"agent_type": agent_name, "status": "online"})
            await self.send(msg)
            print(f"✅ [{agent_name}] Notificação 'alive' enviada ao {self.target}.")
        except Exception as e:
            print(f"❌ [{self.agent.name}] Falha ao enviar notificação 'alive': {e}")
            import traceback
            traceback.print_exc()
