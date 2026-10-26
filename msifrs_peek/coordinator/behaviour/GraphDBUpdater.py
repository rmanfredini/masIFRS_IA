from datetime import datetime
from peak import OneShotBehaviour
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import traceback
import logging

# Configurar logger do peak.database
logger = logging.getLogger("peak.database")
logger.setLevel(logging.INFO)


load_dotenv()

class GraphDBUpdater(OneShotBehaviour):
    """
    Comportamento responsável por centralizar todas as atualizações do GraphDB
    Evita duplicação de código entre os processadores de forecast
    """
    
    def __init__(self, consumption_value=None, generation_value=None, update_type="forecast"):
        super().__init__()
        self.consumption_value = consumption_value or "0.0"
        self.generation_value = generation_value or "0.0"
        self.update_type = update_type  # 'forecast', 'current', etc.
        self.success = False
        
    async def on_start(self):
        #print(f"🔄 [{self.agent.name}] Iniciando GraphDBUpdater para {self.update_type}")
        pass
        
    async def run(self):
        """Executa a atualização do GraphDB"""
        try:
            if self.update_type == "forecast":
                self.success = await self._update_forecast_data()
            else:
                print(f"⚠️ [{self.agent.name}] Tipo de update não suportado: {self.update_type}")
                
        except Exception as e:
            print(f"❌ [{self.agent.name}] Erro no GraphDBUpdater: {e}")
            traceback.print_exc()
            self.success = False
    
    async def _update_forecast_data(self):
        """Atualiza dados de forecast no GraphDB"""
        query = "N/A"
        graphdb_url = "N/A"
        try:
            # Obter credenciais do GraphDB do arquivo .env
            graphdb_url = os.getenv('GRAPHDB_URL')
            graphdb_user = os.getenv('GRAPHDB_USER')
            graphdb_password = os.getenv('GRAPHDB_PASSWORD')
            
            if not all([graphdb_url, graphdb_user, graphdb_password]):
                print("❌ GraphDB credentials not found in .env file")
                return False
            
            # Carregar query de update
            query = self._load_update_sparql_query("update-forecast-data.sparql")
            if not query:
                print("❌ Could not load update query")
                return False
            
            # Substituir placeholders pelos valores reais
            #query = query.replace("<[CONSUMPTION_VALUE]>", str(self.consumption_value))
            #query = query.replace("<[GENERATION_VALUE]>", str(self.generation_value))
            query = query.replace("<[CONSUMPTION_VALUE]>", str(self.generation_value))
            query = query.replace("<[GENERATION_VALUE]>", str(self.consumption_value))

            print(f"🔄 [{self.agent.name}] Updating GraphDB with consumption: {self.consumption_value}, generation: {self.generation_value}")
            #print(f"🌐 GraphDB URL: {graphdb_url}")
            
            # Preparar dados para requisição HTTP
            headers = {
                'Content-Type': 'application/sparql-update',
                'Accept': 'application/json'
            }
            
            # Fazer requisição SPARQL UPDATE para o GraphDB
            response = requests.post(
                f"{graphdb_url}/statements",
                data=query,
                headers=headers,
                auth=HTTPBasicAuth(graphdb_user, graphdb_password),
                timeout=30
            )
            
            escaped_query = query.replace("\n", " [NL] ")
            status = "SUCCESS" if response.status_code == 204 else "ERROR"
            result_details = f"Status {response.status_code}: {response.text.replace(chr(10), ' [NL] ')}"
            logger.info(
                f"[DB_MSG] GRAPHDB | URL: {graphdb_url}/statements | Action: UPDATE | Query: {escaped_query} | Status: {status} | Result: {result_details}"
            )
            
            if response.status_code == 204:  # 204 No Content = sucesso em SPARQL UPDATE
                #print(f"✅ [{self.agent.name}] GraphDB updated successfully")
                return True
            else:
                print(f"❌ [{self.agent.name}] GraphDB update failed. Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            escaped_query = query.replace("\n", " [NL] ")
            logger.error(f"[DB_MSG] GRAPHDB | URL: {graphdb_url}/statements | Action: UPDATE | Query: {escaped_query} | Status: ERROR | Result: ConnectionError: {e}")
            print(f"⚠️ [{self.agent.name}] GraphDB server unavailable: {e}")
            print(f"   💡 Consider checking if GraphDB server is running")
            return False
        except requests.exceptions.Timeout as e:
            escaped_query = query.replace("\n", " [NL] ")
            logger.error(f"[DB_MSG] GRAPHDB | URL: {graphdb_url}/statements | Action: UPDATE | Query: {escaped_query} | Status: ERROR | Result: Timeout: {e}")
            print(f"⚠️ [{self.agent.name}] GraphDB request timeout: {e}")
            return False
        except requests.exceptions.RequestException as e:
            escaped_query = query.replace("\n", " [NL] ")
            logger.error(f"[DB_MSG] GRAPHDB | URL: {graphdb_url}/statements | Action: UPDATE | Query: {escaped_query} | Status: ERROR | Result: RequestException: {e}")
            print(f"❌ [{self.agent.name}] Network error updating GraphDB: {e}")
            return False
        except Exception as e:
            escaped_query = query.replace("\n", " [NL] ")
            logger.error(f"[DB_MSG] GRAPHDB | URL: {graphdb_url}/statements | Action: UPDATE | Query: {escaped_query} | Status: ERROR | Result: Exception: {e}")
            print(f"❌ [{self.agent.name}] Error updating GraphDB: {e}")
            traceback.print_exc()
            return False
    
    def _load_update_sparql_query(self, filename):
        """Carrega query SPARQL UPDATE"""
        filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sparql", "update", filename))
        
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding='utf-8') as sparqlFile:
                    query = sparqlFile.read()
                    return query
            else:
                print(f"❌ SPARQL update file not found: {filepath}")
                return None
        except Exception as e:
            print(f"❌ Error loading SPARQL update file: {e}")
            return None
    
    def get_result(self):
        """Retorna o resultado da operação"""
        return self.success
    
    async def on_end(self):
        status = "✅ SUCESSO" if self.success else "❌ FALHA"
        #print(f"{status} [{self.agent.name}] GraphDBUpdater finalizado - {self.update_type}")
        #print(f"   📊 Consumption: {self.consumption_value} kW")
        #print(f"   📊 Generation: {self.generation_value} kW")
