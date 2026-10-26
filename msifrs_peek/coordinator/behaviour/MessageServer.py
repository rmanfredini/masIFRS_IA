from datetime import datetime
from peak import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from behaviour.ConsumptionForecastInformProcessor import ConsumptionForecastInformProcessor
from behaviour.ConsumptionInformProcessor import ConsumptionInformProcessor 
from behaviour.GenerationInformProcessor import GenerationInformProcessor 
from behaviour.GenerationForecastInformProcessor import GenerationForecastInformProcessor
from behaviour.GenerationExcessRuleProcessor import GenerationExcessRuleProcessor
from behaviour.MultiRuleProcessor import MultiRuleProcessor
from behaviour.GraphDBUpdater import GraphDBUpdater


class MessageServer(CyclicBehaviour):

  async def on_start(self):
    #print("{} - [{}] - Starting Message Server . . .".format(datetime.now(), self.agent.name))
    self.counter = 0
    self.rule_processor_added = False  # Flag para controlar se já foi adicionado
    
  def _check_all_data_available(self):
    """Verifica se todos os dados necessários estão disponíveis para executar as regras"""
    try:
      # Verificar se todos os dados estão presentes no agente
      has_consumption = hasattr(self.agent, 'ultimo_consumo') and self.agent.ultimo_consumo is not None
      has_generation = hasattr(self.agent, 'ultima_geracao') and self.agent.ultima_geracao is not None
      has_consumption_forecast = hasattr(self.agent, 'ultima_previsao_consumo') and self.agent.ultima_previsao_consumo is not None
      has_generation_forecast = hasattr(self.agent, 'previsao_geracao') and self.agent.previsao_geracao is not None
      
      if has_consumption and has_generation and has_consumption_forecast and has_generation_forecast:
        # Verificar se os valores numéricos estão disponíveis
        consumption_value = self.agent.ultimo_consumo.get('valor_consumo') if has_consumption else None
        generation_value = self.agent.ultima_geracao.get('valor_geracao') if has_generation else None
        consumption_forecast_value = self.agent.ultima_previsao_consumo.get('valor_previsao_consumo') if has_consumption_forecast else None
        generation_forecast_value = self.agent.previsao_geracao.get('valor_previsao_geracao') if has_generation_forecast else None
        
        all_values_present = all([
          consumption_value is not None,
          generation_value is not None, 
          consumption_forecast_value is not None,
          generation_forecast_value is not None
        ])
        
        if all_values_present:
          print(f"✅ [{self.agent.name}] Todos os dados necessários disponíveis para regras de excesso:")
          print(f"   📊 Consumo atual: {consumption_value} kW")
          print(f"   📊 Geração atual: {generation_value} kW")
          print(f"   📈 Previsão consumo: {consumption_forecast_value} kW")
          print(f"   📈 Previsão geração: {generation_forecast_value} kW")
          return True
        else:
          missing_values = []
          if consumption_value is None: missing_values.append("consumo atual")
          if generation_value is None: missing_values.append("geração atual")
          if consumption_forecast_value is None: missing_values.append("previsão consumo")
          if generation_forecast_value is None: missing_values.append("previsão geração")
          
          #print(f"⚠️ [{self.agent.name}] Valores numéricos ausentes: {', '.join(missing_values)}")
          return False
      else:
        missing_data = []
        if not has_consumption: missing_data.append("consumo atual")
        if not has_generation: missing_data.append("geração atual") 
        if not has_consumption_forecast: missing_data.append("previsão consumo")
        if not has_generation_forecast: missing_data.append("previsão geração")
        
        #print(f"⚠️ [{self.agent.name}] Dados ausentes: {', '.join(missing_data)}")
        return False
        
    except Exception as e:
      print(f"❌ [{self.agent.name}] Erro ao verificar disponibilidade de dados: {e}")
      return False
  
  def _check_forecast_data_available(self):
    """Verifica se há dados de forecast de geração e consumo disponíveis"""
    try:
      has_consumption_forecast = hasattr(self.agent, 'ultima_previsao_consumo') and self.agent.ultima_previsao_consumo is not None
      has_generation_forecast = hasattr(self.agent, 'previsao_geracao') and self.agent.previsao_geracao is not None
      
      if has_consumption_forecast and has_generation_forecast:
        consumption_forecast_value = self.agent.ultima_previsao_consumo.get('valor_previsao_consumo') if has_consumption_forecast else None
        generation_forecast_value = self.agent.previsao_geracao.get('valor_previsao_geracao') if has_generation_forecast else None
        
        both_forecast_values_present = all([
          consumption_forecast_value is not None,
          generation_forecast_value is not None
        ])
        
        if both_forecast_values_present:
          #print(f"✅ [{self.agent.name}] Dados de forecast disponíveis:")
          #print(f"   📈 Previsão consumo: {consumption_forecast_value} kW")
          #print(f"   📈 Previsão geração: {generation_forecast_value} kW")
          return True, consumption_forecast_value, generation_forecast_value
        else:
          missing_forecast = []
          if consumption_forecast_value is None: missing_forecast.append("previsão consumo")
          if generation_forecast_value is None: missing_forecast.append("previsão geração")
          
          print(f"⚠️ [{self.agent.name}] Valores de forecast ausentes: {', '.join(missing_forecast)}")
          return False, None, None
      else:
        missing_forecast_data = []
        if not has_consumption_forecast: missing_forecast_data.append("previsão consumo")
        if not has_generation_forecast: missing_forecast_data.append("previsão geração")
        
        #print(f"⚠️ [{self.agent.name}] Dados de forecast ausentes: {', '.join(missing_forecast_data)}")
        return False, None, None
        
    except Exception as e:
      print(f"❌ [{self.agent.name}] Erro ao verificar dados de forecast: {e}")
      return False, None, None
  
  def _add_graphdb_updater_if_ready(self):
    """Adiciona GraphDBUpdater se há dados de forecast disponíveis"""
    try:
      has_forecast, consumption_value, generation_value = self._check_forecast_data_available()
      
      if has_forecast:
        #print(f"🔄 [{self.agent.name}] Adicionando GraphDBUpdater para atualizar forecasts...")
        
        # Criar e executar o GraphDBUpdater
        existing_graphdb_updater = any(
          isinstance(behaviour, GraphDBUpdater) 
          for behaviour in getattr(self.agent, '_behaviours', [])
        )

        if not existing_graphdb_updater:
          graphdb_updater = GraphDBUpdater(
            consumption_value=str(consumption_value),
            generation_value=str(generation_value),
            update_type="forecast"
          )       
          # Adicionar como comportamento temporário
          self.agent.add_behaviour(graphdb_updater)
        #print(f"✅ [{self.agent.name}] GraphDBUpdater adicionado para forecast data")
        return True
      else:
        #print(f"⏳ [{self.agent.name}] Aguardando dados de forecast completos para GraphDB update")
        return False
      
    except Exception as e:
      print(f"❌ [{self.agent.name}] Erro ao adicionar GraphDBUpdater: {e}")
      import traceback
      traceback.print_exc()
      return False
  
  def _add_rule_processor_if_ready(self):
    """Adiciona o MultiRuleProcessor se todos os dados estiverem disponíveis"""
    try:
      if not self.rule_processor_added and self._check_all_data_available():
        # Verificar se já existe um MultiRuleProcessor ativo
        existing_rule_processor = any(
          isinstance(behaviour, MultiRuleProcessor)
          for behaviour in getattr(self.agent, '_behaviours', [])
        )
        
        if not existing_rule_processor:
          print(f"🔄 [{self.agent.name}] Adicionando MultiRuleProcessor...")
          
          # Criar e adicionar o processador de múltiplas regras
          rule_processor = MultiRuleProcessor() 
          self.agent.add_behaviour(rule_processor)
          
          self.rule_processor_added = True
          print(f"✅ [{self.agent.name}] MultiRuleProcessor adicionado com sucesso")
        else:
          print(f"💡 [{self.agent.name}] Processador de regras já está ativo")
          self.rule_processor_added = True
      
    except Exception as e:
      print(f"❌ [{self.agent.name}] Erro ao adicionar MultiRuleProcessor: {e}")
      import traceback
      traceback.print_exc()
    
  async def run(self):
    self.rule_processor_added = False
    while msg := await self.receive():
      if msg.thread == "agent-alive-notification":
        # Processar mensagens de notificação "alive" dos agentes
        try:
          import json
          if msg.body and msg.body.strip():
            data = json.loads(msg.body)
            agent_type = data.get("agent_type", "unknown")
            status = data.get("status", "unknown")
            print(f"💓 [{self.agent.name}] Agent '{agent_type}' is {status} (from {msg.sender})")
            
            # Armazenar status do agente
            if not hasattr(self.agent, 'agents_status'):
              self.agent.agents_status = {}
            self.agent.agents_status[agent_type] = {
              'status': status,
              'last_seen': datetime.now().isoformat(),
              'sender': str(msg.sender)
            }
          else:
            print(f"⚠️ [{self.agent.name}] Empty 'alive' notification from {msg.sender}")
        except json.JSONDecodeError as e:
          print(f"❌ [{self.agent.name}] Error parsing 'alive' notification: {e}")
        except Exception as e:
          print(f"❌ [{self.agent.name}] Error processing 'alive' notification: {e}")
        
      elif msg.thread == "current-consumption-inform":
        self.agent.add_behaviour(ConsumptionInformProcessor(msg))
      elif msg.thread == "current-generation-inform":
        self.agent.add_behaviour(GenerationInformProcessor(msg))
      elif msg.thread == "generation-forecast-inform":
        self.agent.add_behaviour(GenerationForecastInformProcessor(msg))
      elif msg.thread == "consumption-forecast-inform":
        self.agent.add_behaviour(ConsumptionForecastInformProcessor(msg))
      elif msg.thread == "active-rule-agree":
        # Director aprovou a ação da regra — ciclo de atuação pode prosseguir
        print(f"✅ [{self.agent.name}] ActiveRuleAgree recebido do Director (de {msg.sender}). Regra aprovada.")
        # TODO: acionar DeviceControlRequest / actuator quando implementado
      elif msg.thread == "active-rule-refuse":
        # Director recusou a ação — cancelar ciclo de atuação
        print(f"🚫 [{self.agent.name}] ActiveRuleRefuse recebido do Director (de {msg.sender}). Ação cancelada por política global.")
      elif msg.thread == "shutdown":
        self.agent.stop() 
      else:
        print(f"⚠️ [{self.agent.name}] Unhandled message thread: '{msg.thread}' from {msg.sender}")
        print(f"   📄 Message content: {msg.body[:100] if msg.body else 'empty'}...")
        response = msg.make_reply()
        response.set_metadata("performative", "not-understood")
        response.body = "Unable to solve your {} message".format(msg.get_metadata("performative"))
        # send message
        await self.send(response)
        
      self._add_rule_processor_if_ready()
      self._add_graphdb_updater_if_ready()      
      self.counter += 1
  
  async def on_end(self):
    #print("{} - [{}] - Ending Message Server . . .".format(datetime.now(), self.agent.name))
    await self.agent.stop()
