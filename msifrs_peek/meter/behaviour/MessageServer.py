from behaviour.CurrentConsumptionInform import CurrentConsumptionInform
from behaviour.CurrentGenerationInform import CurrentGenerationInform
from behaviour.StorageDataInform import StorageDataInform
from datetime import datetime
from peak import CyclicBehaviour, OneShotBehaviour

class MessageServer(CyclicBehaviour):

  async def on_start(self):
    #print("{} - [{}] - Starting Message Server . . .".format(datetime.now(), self.agent.name))
    pass

  async def run(self):
      #print("{} - [{}] - Message Server running . . .".format(datetime.now(), self.agent.name))
      msg = await self.receive()
      if msg.thread == "current-consumption-request":
        cci = CurrentConsumptionInform(msg)
        self.agent.add_behaviour(cci)
      elif msg.thread == "current-generation-request":
        cgi = CurrentGenerationInform(msg)
        self.agent.add_behaviour(cgi)
      elif msg.thread == "storage-data-request":
        sdi = StorageDataInform(msg)
        self.agent.add_behaviour(sdi)
      elif msg.thread == "shutdown":
        self.agent.stop()
      else:
        response = msg.make_reply()
        response.set_metadata("performative", "not-understood")
        response.body = "Unable to solve your {} message".format(msg.get_metadata("performative"))
        # send message
        await self.send(response)

  async def on_end(self):
    #print("{} - [{}] - Ending Message Server . . .".format(datetime.now(), self.agent.name))
    pass