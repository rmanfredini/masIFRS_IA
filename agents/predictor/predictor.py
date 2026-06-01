
from datetime import datetime
from peak import Agent, Message
import os
import sys
import json
import asyncio
from behaviour.MessageServer import MessageServer

class predictor(Agent):

  async def setup(self):
    print("{} - [{}] - Hello! I'm agent {}".format(datetime.now(), self.name, str(self.jid)))
    pass

    # Set predictor.behaviour.MessageServer.MessageServer(CyclicBehaviour)
    msb = MessageServer()
    self.add_behaviour(msb)

    # Enviar notificação 'alive' diretamente como método do agente
    await self.notify_alive()

  async def notify_alive(self):
    """Método simples para notificar que o agente está vivo"""
    try:
      # Uma pequena espera para garantir que a conexão XMPP esteja estabelecida
      await asyncio.sleep(2)

      agent_name = self.name
      coordinator_jid = f"coordinator@{self.jid.domain}"

      print(f"📤 [{agent_name}] Enviando notificação 'alive' para {coordinator_jid}...")

      # Criar a mensagem usando as classes do PEAK
      alive_msg = Message(to=coordinator_jid)
      alive_msg.set_metadata("performative", "inform")
      alive_msg.thread = "agent-alive-notification"
      alive_msg.body = json.dumps({"agent_type": agent_name, "status": "online"})
      
      # Usar o método submit para enviar a mensagem diretamente via SPADE
      raw_msg = alive_msg.prepare()
      await self.client.send(raw_msg)
      
      print(f"✅ [{agent_name}] Notificação 'alive' enviada com sucesso.")

    except Exception as e:
      print(f"❌ [{self.name}] Falha ao enviar notificação 'alive': {e}")
      import traceback
      traceback.print_exc()