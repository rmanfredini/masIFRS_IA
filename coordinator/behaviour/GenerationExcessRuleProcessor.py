from datetime import datetime
from peak import OneShotBehaviour, PeriodicBehaviour
import json
import rdflib
import os
import traceback
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

class GenerationExcessRuleProcessor(OneShotBehaviour):
    """
    Comportamento que executa a query de regra de excesso de geração
    Verifica se a geração excede o consumo e determina ações a serem tomadas
    """
    
    def __init__(self):  # Executa a cada 60 segundos por padrão
        super().__init__()
        self.sparql_filename = "generation-excess-rule.sparql"
        self.sparql_cache = {}
        self.executed_count = 0
        self.last_actions = []
        
    async def on_start(self):
        print(f"🔄 [{self.agent.name}] Iniciando GenerationExcessRuleProcessor...")

    async def run(self):
        """Executa a verificação de regras de excesso de geração"""
        try:
            print(f"⚡ [{self.agent.name}] Executando verificação de regras de excesso de geração...")
            
            # Carregar e executar query SPARQL
            query = self._load_sparql_query()
            if not query:
                print(f"❌ Não foi possível carregar a query SPARQL")
                return
            
            # Executar query no GraphDB
            results = await self._execute_sparql_query(query)
            if not results:
                print(f"⚠️ Nenhum resultado retornado da query")
                return
                            
            # Processar resultados
            actions = self._process_query_results(results)
            print(f"✅ [{self.agent.name}] Query executada com sucesso no GraphDB", actions)
            if actions:
                print(f"🎯 [{self.agent.name}] {len(actions)} ações identificadas:")
                for i, action in enumerate(actions, 1):
                    print(f"   {i}. {action.get('action_description', 'Ação sem descrição')}")
                    print(f"      📱 Dispositivo: {action.get('actuate_on_device', {}).get('device_id', 'N/A')}")
                    print(f"      🔧 Estado atual: {action.get('actuate_on_device', {}).get('current_state', 'N/A')}")
                    print(f"      ➡️ Novo estado: {action.get('actuate_on_device', {}).get('set_state', 'N/A')}")
                
                # Armazenar ações para possível execução
                self.last_actions = actions
                
                # Executar ações se habilitado
                if hasattr(self.agent, 'execute_actions') and self.agent.execute_actions:
                    await self._execute_actions(actions)
                else:
                    print(f"💡 [{self.agent.name}] Ações identificadas mas não executadas (modo simulação)")
            else:
                print(f"✅ [{self.agent.name}] Nenhuma ação necessária - geração dentro dos limites")
            
            self.executed_count += 1
            
        except Exception as e:
            print(f"❌ Erro no GenerationExcessRuleProcessor: {e}")
            traceback.print_exc()
    
    def _load_sparql_query(self):
        """Carrega a query SPARQL de regras de excesso de geração"""
        if self.sparql_filename in self.sparql_cache:
            return self.sparql_cache[self.sparql_filename]
        
        filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sparql", "rules", self.sparql_filename))
        
        try:
            if os.path.isfile(filepath):
                with open(filepath, "r", encoding='utf-8') as sparqlFile:
                    query = sparqlFile.read()
                    self.sparql_cache[self.sparql_filename] = query
                    return query
            else:
                print(f"❌ Arquivo SPARQL não encontrado: {filepath}")
                return None
        except Exception as e:
            print(f"❌ Erro ao carregar arquivo SPARQL {self.sparql_filename}: {e}")
            return None
    
    async def _execute_sparql_query(self, query):
        """Executa a query SPARQL no GraphDB remoto"""
        try:
            # Obter credenciais do GraphDB
            graphdb_url = os.getenv('GRAPHDB_URL')
            graphdb_user = os.getenv('GRAPHDB_USER')
            graphdb_password = os.getenv('GRAPHDB_PASSWORD')
            
            if not all([graphdb_url, graphdb_user, graphdb_password]):
                print("❌ Credenciais do GraphDB não encontradas no arquivo .env")
                return None
            
            # Preparar requisição SPARQL
            headers = {
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            }
            
            # Fazer requisição para o GraphDB
            response = requests.post(
                f"{graphdb_url}",
                data=query,
                headers=headers,
                auth=HTTPBasicAuth(graphdb_user, graphdb_password),
                timeout=30
            )
            
            if response.status_code == 200:
                result_data = response.json()
                print(f"✅ [{self.agent.name}] Query executada com sucesso no GraphDB")
                print(f"   Resultados: {result_data}")
                return result_data
            else:
                print(f"❌ [{self.agent.name}] Falha na query. Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ [{self.agent.name}] Servidor GraphDB indisponível: {e}")
            return None
        except requests.exceptions.Timeout as e:
            print(f"⚠️ [{self.agent.name}] Timeout na requisição GraphDB: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ [{self.agent.name}] Erro de rede ao consultar GraphDB: {e}")
            return None
        except Exception as e:
            print(f"❌ [{self.agent.name}] Erro ao executar query no GraphDB: {e}")
            return None
    
    def _process_query_results(self, results):
        """Processa os resultados da query SPARQL"""
        try:
            actions = []
            
            if 'results' in results and 'bindings' in results['results']:
                for binding in results['results']['bindings']:
                    if 'dict' in binding and 'value' in binding['dict']:
                        dict_value = binding['dict']['value']
                        print(f"🔍 Processando dict: {dict_value}")
                        # Se o dict não estiver vazio, significa que uma regra foi ativada
                        if dict_value: #and dict_value != "{}":
                            try:
                                action_data = json.loads(dict_value)
                                actions.append(action_data)
                            except json.JSONDecodeError as e:
                                print(f"⚠️ Erro ao processar JSON de ação: {e}")
                                print(f"   Valor problemático: {dict_value}")
            
            return actions
            
        except Exception as e:
            print(f"❌ Erro ao processar resultados da query: {e}")
            return []
    
    async def _execute_actions(self, actions):
        """Executa as ações identificadas pelas regras"""
        try:
            print(f"🚀 [{self.agent.name}] Executando {len(actions)} ações...")
            
            for action in actions:
                await self._execute_single_action(action)
                
        except Exception as e:
            print(f"❌ Erro ao executar ações: {e}")
            traceback.print_exc()
    
    async def _execute_single_action(self, action):
        """Executa uma única ação"""
        try:
            action_id = action.get('action_id', 'unknown')
            action_description = action.get('action_description', 'Ação sem descrição')
            device_info = action.get('actuate_on_device', {})
            device_id = device_info.get('device_id', 'unknown')
            new_state = device_info.get('set_state', 'unknown')
            
            print(f"⚡ [{self.agent.name}] Executando ação {action_id}:")
            print(f"   📝 Descrição: {action_description}")
            print(f"   📱 Dispositivo: {device_id}")
            print(f"   🔧 Novo estado: {new_state}")
            
            # Aqui você pode implementar a lógica específica para cada tipo de ação
            # Por exemplo, enviar comandos para dispositivos, atualizar estados, etc.
            
            if device_info.get('is_controlable', False):
                # Simular execução da ação (implementar lógica real conforme necessário)
                print(f"✅ [{self.agent.name}] Ação simulada para dispositivo controlável {device_id}")
                
                # Aqui você poderia:
                # 1. Enviar mensagem XMPP para agente actuator
                # 2. Fazer chamada HTTP para API do dispositivo
                # 3. Atualizar estado no GraphDB
                # 4. Registrar ação em log de auditoria
                
            else:
                print(f"⚠️ [{self.agent.name}] Dispositivo {device_id} não é controlável")
            
        except Exception as e:
            print(f"❌ Erro ao executar ação individual: {e}")
    
    def get_status(self):
        """Retorna status atual do processador"""
        return {
            'processor_type': 'GenerationExcessRuleProcessor',
            'executed_count': self.executed_count,
            'period_seconds': self.period,
            'last_actions_count': len(self.last_actions),
            'sparql_file': self.sparql_filename
        }
    
    def get_last_actions(self):
        """Retorna as últimas ações identificadas"""
        return self.last_actions.copy()
    
    async def on_end(self):
        print(f"🏁 [{self.agent.name}] GenerationExcessRuleProcessor finalizado")
        print(f"   📊 Total de execuções: {self.executed_count}")
        print(f"   🎯 Últimas ações identificadas: {len(self.last_actions)}")
