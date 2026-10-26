from datetime import datetime
from peak import  Message, OneShotBehaviour
import json
import asyncio


class Alive(OneShotBehaviour):
    async def on_start(self):
        # Não é necessário definir o nome aqui. Usaremos o nome real do agente.
        #print(f"[{self.agent.name}] - Comportamento 'Alive' iniciado.")
        pass

    async def run(self):
        try:
            # Uma pequena espera para garantir que a conexão XMPP esteja estabelecida
            await asyncio.sleep(2)

            # CORREÇÃO: O JID e o nome pertencem ao AGENTE, não ao comportamento.
            # Use 'self.agent.jid' e 'self.agent.name'.
            agent_name = self.agent.name
            coordinator_jid = f"coordinator@{self.agent.jid.domain}"

            #print(f"📤 [{agent_name}] Enviando notificação 'alive' para {coordinator_jid}...")

            alive_msg = Message(to=coordinator_jid)
            alive_msg.set_metadata("performative", "inform")
            # Usamos uma thread específica para identificar esta mensagem
            alive_msg.thread = "agent-alive-notification"
            # Usar o nome real do agente no corpo da mensagem torna o código reutilizável
            alive_msg.body = json.dumps({"agent_type": agent_name, "status": "online"})
            
            await self.send(alive_msg)
            #print(f"✅ [{agent_name}] Notificação 'alive' enviada com sucesso.")

            # MELHORIA: Como a mensagem 'alive' só precisa ser enviada uma vez,
            # o comportamento se encerra automaticamente por ser OneShotBehaviour
            #print(f"[{agent_name}] - Comportamento 'Alive' concluído. Encerrando...")

        except Exception as e:
            # Usar self.agent.name para o log de erro
            print(f"❌ [{self.agent.name}] Falha ao enviar notificação 'alive': {e}")
            import traceback
            traceback.print_exc()
            # OneShotBehaviour se encerra automaticamente mesmo em caso de erro


