import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import util.agent_patch

from behaviour.MessageServer import MessageServer
from behaviour.StartAgent import StartAgent
from datetime import datetime
from spade.agent import Agent
from util.spade_runner import run_agent


class coordinator(Agent):

  async def setup(self):
    print("{} - [{}] - Hello! I'm agent {}".format(datetime.now(), self.name, str(self.jid)))

    # StartAgent aguarda o 'alive' dos agentes filhos e então adiciona
    # os comportamentos operacionais ao coordinator.
    self.add_behaviour(MessageServer())
    self.add_behaviour(StartAgent(campus_id=1, period=60, timeout=6))

    print(f"✅ [{self.name}] Coordinator setup completed - StartAgent will initialize child agents")


if __name__ == "__main__":
  run_agent(coordinator)
