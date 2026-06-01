import asyncio
import platform

from behaviour.MessageServer import MessageServer
from behaviour.CurrentConsumptionRequest import CurrentConsumptionRequest
from behaviour.CurrentGenerationRequest import CurrentGenerationRequest
from behaviour.GenerationForecastRequest import GenerationForecastRequest
from behaviour.ConsumptionForecastRequest import ConsumptionForecastRequest
from behaviour.StartAgent import StartAgent
#from behaviour.StorageDataRequest import StorageDataRequest
from datetime import datetime
from peak import Agent, CyclicBehaviour
import asyncio

class coordinator(Agent):

  async def setup(self):
    print("{} - [{}] - Hello! I'm agent {}".format(datetime.now(), self.name, str(self.jid)))
    
    # Adicionar StartAgent como comportamento para inicializar outros agentes
    # O StartAgent irá adicionar o MessageServer e outros comportamentos quando os agentes estiverem prontos
    
    msg= MessageServer()
    self.add_behaviour(msg) 
    
    start_agent = StartAgent(campus_id=1, period=60, timeout=6)  # Executa a cada 1 minuto
    self.add_behaviour(start_agent)
    
    print(f"✅ [{self.name}] Coordinator setup completed - StartAgent will initialize child agents")
