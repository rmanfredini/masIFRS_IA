from .MessageServer import MessageServer
from .CurrentConsumptionRequest import CurrentConsumptionRequest
from .CurrentGenerationRequest import CurrentGenerationRequest
from .GenerationForecastRequest import GenerationForecastRequest
from .ConsumptionForecastRequest import ConsumptionForecastRequest
from .ConsumptionInformProcessor import ConsumptionInformProcessor
from .GenerationInformProcessor import GenerationInformProcessor
from .ConsumptionForecastInformProcessor import ConsumptionForecastInformProcessor
from .GenerationForecastInformProcessor import GenerationForecastInformProcessor
from peak.bootloader import boot_agent
from multiprocessing import Process
from datetime import datetime, timedelta
from peak import OneShotBehaviour, JID, CyclicBehaviour, PeriodicBehaviour
from pathlib import Path
import asyncio
import os
import json

class StartAgent(PeriodicBehaviour):
    def __init__(self, campus_id, period=20, timeout=6):
        super().__init__(period=period)  # Chama o construtor do PeriodicBehaviour
        self.campus_id = campus_id
        self.timeout = timeout
        self.iteracao = 1
            
    async def run(self):
        try:
            print(f"▶️  [{self.agent.name}] Comportamento StartAgent iniciado. Lançando agentes filhos...")
            #print("\n⏳ Aguardando confirmação 'alive' dos agentes...")
            agents_alive = set()
            expected_agents = { "meter","predictor"}
            timeout_seconds = 60
            wait_start_time = datetime.now()
            if self.iteracao == 1:
                while len(agents_alive) < len(expected_agents):
                    if datetime.now() - wait_start_time > timedelta(seconds=timeout_seconds):
                        print(f"❌ TIMEOUT: Atingido o tempo limite de {timeout_seconds}s.")
                        break
                    try:
                        msg = await self.receive(timeout=5.0)
                        if msg and msg.thread == "agent-alive-notification":
                            # Verificar se msg.body não está vazio antes de tentar fazer parse do JSON
                            if msg.body and msg.body.strip():
                                try:
                                    data = json.loads(msg.body)
                                    agent_type = data.get("agent_type")
                                    if agent_type not in agents_alive:
                                        #print(f"   ✅ Confirmação 'alive' recebida de: {agent_type.upper()}")
                                        agents_alive.add(agent_type)
                                except json.JSONDecodeError as json_err:
                                    print(f"   ⚠️ Erro ao processar JSON na mensagem 'alive': {json_err}")
                                    print(f"   📄 Conteúdo da mensagem: '{msg.body}'")
                            else:
                                print(f"   ⚠️ Mensagem 'alive' recebida com corpo vazio")
                    except asyncio.TimeoutError:
                        print("   ...ainda aguardando...")
                        continue
            
            # CORREÇÃO: Se os agentes estiverem vivos, ESTE comportamento adiciona os outros.
            if (agents_alive == expected_agents or self.iteracao > 1): # and not hasattr(self.agent, '_behaviours_added'):
                
                print("\n🎉 SUCESSO: Todos os agentes confirmaram. Adicionando comportamentos operacionais ao coordinator...")
                
                # Marcar que os comportamentos foram adicionados para evitar duplicação
                self.agent._behaviours_added = True
                
                # Usamos self.agent para acessar o coordinator e adicionar comportamentos a ele.
                #self.agent.add_behaviour(MessageServer())
                self.agent.add_behaviour(CurrentConsumptionRequest())
                self.agent.add_behaviour(CurrentGenerationRequest())
                self.agent.add_behaviour(GenerationForecastRequest())
                self.agent.add_behaviour(ConsumptionForecastRequest())
                
                print("✅ Coordinator está totalmente operacional.")
            elif agents_alive != expected_agents and self.iteracao == 1:
                print("\n⚠️ FALHA: Nem todos os agentes confirmaram. O coordinator não será totalmente iniciado.")
            
            self.iteracao += 1
        except Exception as e:
            print(f"❌ ERRO CRÍTICO no StartAgent: {e}")
            import traceback
            traceback.print_exc()
        
        print("🏁 Comportamento StartAgent concluído.")