from datetime import datetime
from peak import CyclicBehaviour

class MessageServer(CyclicBehaviour):

  async def on_start(self):
    print("{} - [{}] - Starting Message Server . . .".format(datetime.now(), self.agent.name))
    self.counter = 0

  async def run(self):
    if msg := await self.receive():
      if msg.thread == "device-control-request":
        # TODO: implementar DeviceControlInform
        print("{} - [{}] - Received device-control-request (not yet implemented)".format(
          datetime.now(), self.agent.name))
        response = msg.make_reply()
        response.thread = "device-control-inform"
        response.set_metadata("performative", "agree")
        response.body = "Device control request received."
        await self.send(response)
      elif msg.thread == "shutdown":
        self.agent.stop()
      else:
        response = msg.make_reply()
        response.set_metadata("performative", "not-understood")
        response.body = "Unable to solve your {} message".format(msg.get_metadata("performative"))
        await self.send(response)

      self.counter += 1

  async def on_end(self):
    print("{} - [{}] - Ending Message Server . . .".format(datetime.now(), self.agent.name))
