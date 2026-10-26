import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import util.agent_patch

from datetime import datetime
from peak import Agent, Message
import os
import sys
import json
import asyncio
from behaviour.MessageServer import MessageServer

class actuator(Agent):

  async def setup(self):
    print("{} - [{}] - Hello! I'm agent {}".format(datetime.now(), self.name, str(self.jid)))

    # Set actuator.behaviour.MessageServer.MessageServer(CyclicBehaviour)
    msb = MessageServer()
    self.add_behaviour(msb)
