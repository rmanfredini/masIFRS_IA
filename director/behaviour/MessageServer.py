from datetime import datetime
from peak import CyclicBehaviour
from behaviour.ActiveRuleInformProcessor import ActiveRuleInformProcessor
from behaviour.StorageDataInformProcessor import StorageDataInformProcessor


class MessageServer(CyclicBehaviour):
    """
    Servidor de mensagens do agente Director.
    Despacha mensagens recebidas para os comportamentos adequados:
      - active-rule-inform       → ActiveRuleInformProcessor
      - storage-data-inform      → StorageDataInformProcessor
    """

    async def on_start(self):
        print("{} - [{}] - Starting Director Message Server . . .".format(
            datetime.now(), self.agent.name))
        self.counter = 0

    async def run(self):
        msg = await self.receive()
        if msg is None:
            return

        thread = msg.thread or ""

        if thread == "active-rule-inform":
            # Coordinator informou que uma regra foi disparada
            processor = ActiveRuleInformProcessor(msg)
            self.agent.add_behaviour(processor)

        elif thread == "storage-data-inform":
            # Meter respondeu com o estado atual do banco de baterias
            processor = StorageDataInformProcessor(msg)
            self.agent.add_behaviour(processor)

        elif thread == "shutdown":
            await self.agent.stop()

        else:
            response = msg.make_reply()
            response.set_metadata("performative", "not-understood")
            response.body = "Unable to solve your {} message".format(
                msg.get_metadata("performative"))
            await self.send(response)

        self.counter += 1

    async def on_end(self):
        print("{} - [{}] - Ending Director Message Server . . .".format(
            datetime.now(), self.agent.name))
        await self.agent.stop()
