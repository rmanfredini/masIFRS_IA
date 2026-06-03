from datetime import datetime
from peak import OneShotBehaviour
import json
import rdflib
import os
import traceback
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import glob

load_dotenv()

class MultiRuleProcessor(OneShotBehaviour):
    """
    Comportamento que executa múltiplas regras SPARQL do diretório rules/
    Processa todas as regras encontradas em cada ciclo
    """
    
    def __init__(self):
        super().__init__()
        self.rules_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sparql", "rules"))
        self.sparql_cache = {}
        self.executed_count = 0
        self.last_actions = {}  # Dicionário com ações por regra
        self.rule_files = []
        
    async def on_start(self):
        """Inicializa o processador e carrega lista de regras"""
        print(f"🔄 [{self.agent.name}] Iniciando MultiRuleProcessor...")
        print(f"   📁 Diretório de regras: {self.rules_directory}")
        
        # Carregar lista de arquivos de regras
        self._load_rule_files()
        
    def _load_rule_files(self):
        """Carrega a lista de arquivos de regras SPARQL"""
        try:
            if not os.path.exists(self.rules_directory):
                print(f"❌ Diretório de regras não encontrado: {self.rules_directory}")
                return
            
            # Buscar todos os arquivos .sparql no diretório
            pattern = os.path.join(self.rules_directory, "*.sparql")
            self.rule_files = glob.glob(pattern)
            
            if not self.rule_files:
                print(f"⚠️ Nenhum arquivo de regra encontrado em {self.rules_directory}")
                return
            
            print(f"📋 [{self.agent.name}] {len(self.rule_files)} regras encontradas:")
            for i, rule_file in enumerate(self.rule_files, 1):
                rule_name = os.path.basename(rule_file)
                print(f"   {i}. {rule_name}")
                
        except Exception as e:
            print(f"❌ Erro ao carregar lista de regras: {e}")
            self.rule_files = []

    async def run(self):
        """Executa todas as regras em cada ciclo"""
        try:
            if not self.rule_files:
                print(f"⚠️ [{self.agent.name}] Nenhuma regra disponível para execução")
                return
            
            print(f"⚡ [{self.agent.name}] Executando {len(self.rule_files)} regras...")
            
            total_actions = 0
            
            # Executar cada regra
            for rule_file in self.rule_files:
                rule_name = os.path.basename(rule_file)
                print(f"\n🔍 [{self.agent.name}] Processando regra: {rule_name}")
                
                try:
                    # Carregar e executar query SPARQL
                    query = self._load_sparql_query(rule_file)
                    if not query:
                        print(f"❌ Não foi possível carregar a query: {rule_name}")
                        continue
                    
                    # Executar query no GraphDB
                    results = await self._execute_sparql_query(query, rule_name)
                    if not results:
                        print(f"⚠️ Nenhum resultado para regra: {rule_name}")
                        continue
                    
                    # Processar resultados
                    actions = self._process_query_results(results, rule_name)
                    self.last_actions[rule_name] = actions
                    
                    if actions:
                        print(f"🎯 [{self.agent.name}] {len(actions)} ações identificadas para {rule_name}:")
                        for i, action in enumerate(actions, 1):
                            print(f"   {i}. {action.get('action_description', 'Ação sem descrição')}")
                            print(f"      📱 Dispositivo: {action.get('actuate_on_device', {}).get('device_id', 'N/A')}")
                            print(f"      🔧 Estado atual: {action.get('actuate_on_device', {}).get('current_state', 'N/A')}")
                            print(f"      ➡️ Novo estado: {action.get('actuate_on_device', {}).get('set_state', 'N/A')}")
                        
                        total_actions += len(actions)
                        
                        # Executar ações se habilitado
                        if hasattr(self.agent, 'execute_actions') and self.agent.execute_actions:
                            await self._execute_actions(actions, rule_name)
                        else:
                            print(f"💡 [{self.agent.name}] Ações identificadas mas não executadas (modo simulação)")
                    else:
                        print(f"✅ [{self.agent.name}] Nenhuma ação necessária para {rule_name}")
                        
                except Exception as e:
                    print(f"❌ Erro ao processar regra {rule_name}: {e}")
                    traceback.print_exc()
            
            print(f"\n📊 [{self.agent.name}] Ciclo completo - Total de ações: {total_actions}")
            self.executed_count += 1
            if total_actions == 0:
                print(f"   ✅Criar mensagem de stand by para o atuador")
            else:
                print(f"   ✅ Ações executadas de charge recharge {total_actions}")
                print(actions)
        except Exception as e:
            print(f"❌ Erro no MultiRuleProcessor: {e}")
            traceback.print_exc()
    
    def _load_sparql_query(self, rule_file):
        """Carrega uma query SPARQL específica"""
        if rule_file in self.sparql_cache:
            return self.sparql_cache[rule_file]
        
        try:
            if os.path.isfile(rule_file):
                with open(rule_file, "r", encoding='utf-8') as sparqlFile:
                    query = sparqlFile.read()
                    self.sparql_cache[rule_file] = query
                    return query
            else:
                print(f"❌ Arquivo SPARQL não encontrado: {rule_file}")
                return None
        except Exception as e:
            print(f"❌ Erro ao carregar arquivo SPARQL {rule_file}: {e}")
            return None
    
    async def _execute_sparql_query(self, query, rule_name):
        """Executa uma query SPARQL no GraphDB remoto"""
        try:
            # Obter credenciais do GraphDB
            graphdb_url = os.getenv('GRAPHDB_URL')
            graphdb_user = os.getenv('GRAPHDB_USER')
            graphdb_password = os.getenv('GRAPHDB_PASSWORD')
            
            if not all([graphdb_url, graphdb_user, graphdb_password]):
                print(f"❌ Credenciais do GraphDB não encontradas no arquivo .env")
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
                print(f"✅ [{self.agent.name}] Query {rule_name} executada com sucesso")
                print(f"   Resultados: {result_data}")
                return result_data
            else:
                print(f"❌ [{self.agent.name}] Falha na query {rule_name}. Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ [{self.agent.name}] Servidor GraphDB indisponível para {rule_name}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            print(f"⚠️ [{self.agent.name}] Timeout na requisição GraphDB para {rule_name}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ [{self.agent.name}] Erro de rede ao consultar GraphDB para {rule_name}: {e}")
            return None
        except Exception as e:
            print(f"❌ [{self.agent.name}] Erro ao executar query {rule_name} no GraphDB: {e}")
            return None
    
    def _process_query_results(self, results, rule_name):
        """Processa os resultados de uma query SPARQL"""
        try:
            actions = []
            
            if 'results' in results and 'bindings' in results['results']:
                for binding in results['results']['bindings']:
                    if 'dict' in binding and 'value' in binding['dict']:
                        dict_value = binding['dict']['value']
                        # Se o dict não estiver vazio, significa que uma regra foi ativada
                        if dict_value and dict_value != "{}":
                            try:
                                action_data = json.loads(dict_value)
                                action_data['rule_file'] = rule_name  # Adicionar referência da regra
                                actions.append(action_data)
                            except json.JSONDecodeError as e:
                                print(f"⚠️ Erro ao processar JSON de ação em {rule_name}: {e}")
                                print(f"   Valor problemático: {dict_value}")
            
            return actions
            
        except Exception as e:
            print(f"❌ Erro ao processar resultados da query {rule_name}: {e}")
            return []
    
    async def _execute_actions(self, actions, rule_name):
        """Executa as ações identificadas por uma regra específica"""
        try:
            print(f"🚀 [{self.agent.name}] Executando {len(actions)} ações para {rule_name}...")
            
            for action in actions:
                await self._execute_single_action(action, rule_name)
                
        except Exception as e:
            print(f"❌ Erro ao executar ações de {rule_name}: {e}")
            traceback.print_exc()
    
    async def _execute_single_action(self, action, rule_name):
        """Executa uma única ação"""
        try:
            action_id = action.get('action_id', 'unknown')
            action_description = action.get('action_description', 'Ação sem descrição')
            device_info = action.get('actuate_on_device', {})
            device_id = device_info.get('device_id', 'unknown')
            new_state = device_info.get('set_state', 'unknown')
            
            print(f"⚡ [{self.agent.name}] Executando ação {action_id} (regra: {rule_name}):")
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
            print(f"❌ Erro ao executar ação individual de {rule_name}: {e}")
    
    def get_status(self):
        """Retorna status atual do processador"""
        return {
            'processor_type': 'MultiRuleProcessor',
            'executed_count': self.executed_count,
            'rules_count': len(self.rule_files),
            'rules_loaded': [os.path.basename(f) for f in self.rule_files],
            'last_actions_by_rule': {rule: len(actions) for rule, actions in self.last_actions.items()}
        }
    
    def get_last_actions(self, rule_name=None):
        """Retorna as últimas ações identificadas, filtradas por regra se especificado"""
        if rule_name:
            return self.last_actions.get(rule_name, []).copy()
        else:
            return {rule: actions.copy() for rule, actions in self.last_actions.items()}
    
    def refresh_rules(self):
        """Recarrega a lista de regras do diretório"""
        print(f"🔄 [{self.agent.name}] Recarregando lista de regras...")
        self.sparql_cache.clear()  # Limpar cache
        self._load_rule_files()
    
    async def on_end(self):
        print(f"🏁 [{self.agent.name}] MultiRuleProcessor finalizado")
        print(f"   📊 Total de execuções: {self.executed_count}")
        print(f"   📋 Regras processadas: {len(self.rule_files)}")
        print(f"   🎯 Total de ações identificadas: {sum(len(actions) for actions in self.last_actions.values())}")
