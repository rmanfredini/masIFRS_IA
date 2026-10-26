import os
import rdflib
from datetime import datetime
from peak import Message, OneShotBehaviour

class StorageDataInform(OneShotBehaviour):

  def __init__(self, msg: Message):
    super().__init__()
    self.message = msg

  async def on_start(self):
    print("{} - [{}] - Starting StorageDataInform . . .".format(datetime.now(), self.agent.name))

  async def run(self):
    print("---<<<<")
    print(self.message)
  
  async def on_end(self):
    print("{} - [{}] - Ending StorageDataInform . . .".format(datetime.now(), self.agent.name))