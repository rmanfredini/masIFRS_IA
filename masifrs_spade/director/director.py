import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import util.agent_patch

from behaviour.MessageServer import MessageServer
from datetime import datetime
from spade.agent import Agent
from util.alive import NotifyAlive
from util.spade_runner import run_agent


class director(Agent):

    async def setup(self):
        print("{} - [{}] - Hello! I'm agent {}".format(datetime.now(), self.name, str(self.jid)))

        # Iniciar servidor de mensagens
        self.add_behaviour(MessageServer())

        # Notificar coordinator que o agente está online
        self.add_behaviour(NotifyAlive())

        print(f"✅ [{self.name}] Director setup completed")


if __name__ == "__main__":
    run_agent(director)
