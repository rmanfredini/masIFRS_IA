import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import util.agent_patch

from behaviour.MessageServer import MessageServer
from datetime import datetime
from spade.agent import Agent
from util.alive import NotifyAlive
from util.spade_runner import run_agent


class meter(Agent):

  async def setup(self):
    # Set meter.behaviour.MessageServer.MessageServer(CyclicBehaviour)
    self.add_behaviour(MessageServer())

    # Notifica o coordinator que o agente está vivo
    self.add_behaviour(NotifyAlive())


if __name__ == "__main__":
  run_agent(meter)