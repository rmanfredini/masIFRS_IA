import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import util.agent_patch

from datetime import datetime
from spade.agent import Agent
from behaviour.MessageServer import MessageServer
from util.alive import NotifyAlive
from util.spade_runner import run_agent


class predictor(Agent):

  async def setup(self):
    print("{} - [{}] - Hello! I'm agent {}".format(datetime.now(), self.name, str(self.jid)))

    # Set predictor.behaviour.MessageServer.MessageServer(CyclicBehaviour)
    self.add_behaviour(MessageServer())

    # Notifica o coordinator que o agente está vivo
    self.add_behaviour(NotifyAlive())


if __name__ == "__main__":
  run_agent(predictor)