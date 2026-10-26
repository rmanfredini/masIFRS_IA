import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import util.agent_patch

from behaviour.MessageServer import MessageServer
from datetime import datetime
from peak import Agent
import asyncio
import json


class director(Agent):

    async def setup(self):
        print("{} - [{}] - Hello! I'm agent {}".format(datetime.now(), self.name, str(self.jid)))

        # Iniciar servidor de mensagens
        msb = MessageServer()
        self.add_behaviour(msb)

        # Notificar coordinator que o agente está online
        await self._notify_alive()

        print(f"✅ [{self.name}] Director setup completed")

    async def _notify_alive(self):
        """Notifica o coordinator que o agente Director está online"""
        try:
            from peak import Message
            await asyncio.sleep(2)

            coordinator_jid = f"coordinator@{self.jid.domain}"
            alive_msg = Message(to=coordinator_jid)
            alive_msg.set_metadata("performative", "inform")
            alive_msg.thread = "agent-alive-notification"
            alive_msg.body = json.dumps({"agent_type": self.name, "status": "online"})

            raw_msg = alive_msg.prepare()
            await self.client.send(raw_msg)

            print(f"✅ [{self.name}] Notificação 'alive' enviada ao coordinator.")

        except Exception as e:
            print(f"❌ [{self.name}] Falha ao enviar notificação 'alive': {e}")
            import traceback
            traceback.print_exc()
