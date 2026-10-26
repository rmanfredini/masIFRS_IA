from behaviour.ConsumptionForecastInform import ConsumptionForecastInform
from behaviour.GenerationForecastInform import GenerationForecastInform
from datetime import datetime
from peak import CyclicBehaviour, OneShotBehaviour

class MessageServer(CyclicBehaviour):

  async def on_start(self):
    #print("{} - [{}] - Starting Message Server . . .".format(datetime.now(), self.agent.name))
    self.counter = 0

  async def run(self):
    while msg := await self.receive():
      #print(msg)  
      if msg.thread == "consumption-forecast-request":
        cci = ConsumptionForecastInform(msg)
        self.agent.add_behaviour(cci)
      elif msg.thread == "generation-forecast-request":
        cgi = GenerationForecastInform(msg)
        self.agent.add_behaviour(cgi)
      elif msg.thread == "shutdown":
        self.agent.stop()
      else:
        response = msg.make_reply()
        response.set_metadata("performative", "not-understood")
        response.body = "Unable to solve your {} message".format(msg.get_metadata("performative"))
        # send message
        await self.send(response)
      
      self.counter += 1
      

  async def on_end(self):
    #print("{} - [{}] - Ending Message Server . . .".format(datetime.now(), self.agent.name))
    pass
    