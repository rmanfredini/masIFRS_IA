from datetime import datetime
from peak import OneShotBehaviour
import json
import rdflib
import os
import traceback
from dotenv import load_dotenv


load_dotenv()
CAMPUS_ID = os.getenv('CAMPUS_ID')

class ConsumptionInformProcessor(OneShotBehaviour):
    """
    Processa mensagens CurrentConsumptionInform do Meter via XMPP direto
    """

    def __init__(self,msg=None):
        super().__init__()
        self.message_type = "CurrentConsumptionInform"
        self.thread_filter = "current-consumption-inform"
        self.sparql_filename = "get-current-consumption-inform-data.sparql"
        self.sparql_cache = {}
        self.processed_count = 0
        self.msg=msg

    async def on_start(self):
        #print("{} - [{}] - Starting ConsumptionInformProcessor for thread '{}' . . .".format(
        #    datetime.now(), self.agent.name, self.thread_filter))
        pass

    async def run(self):
        """Main loop - escuta mensagens XMPP diretamente"""
        try:
            # Receber mensagem diretamente do XMPP com timeout
            msg = self.msg
                        
            if msg:
                # Verificar se esta mensagem é para este processador
                if self._should_process_message(msg):
                    #print(f"✅ ConsumptionInformProcessor processing message from {msg.sender}")
                    await self.process_message(msg)
                    self.processed_count += 1
                # Se não for para este processador, ignora (outros processadores vão tratar)
                    
        except Exception as e:
            print(f"❌ Error in ConsumptionInformProcessor: {e}")
            traceback.print_exc()

    def _should_process_message(self, msg):
        """Determina se este processador deve tratar esta mensagem"""
        try:
            # Verificar thread
            if self.thread_filter and msg.thread != self.thread_filter:
                return False
            
            # Verificar performative (deve ser 'inform' para mensagens de dados)
            performative = msg.get_metadata("performative")
            if performative != "inform":
                return False
            
            # Verificar se mensagem tem conteúdo
            if not msg.body:
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking message filter: {e}")
            return False

    async def process_message(self, msg):
        """Processa mensagem de consumo"""
        try:
            #print("{} - [{}] - Processing {} from {} (thread: {})".format(
            #   datetime.now(), self.agent.name, self.message_type, msg.sender, msg.thread))
            
            # Carregar e executar query SPARQL
            query = self._load_sparql_query()
            if not query:
                print(f"❌ No SPARQL query loaded for {self.message_type}")
                return

            sparqlResult = self._execute_sparql_query(msg, query)
            if not sparqlResult:
                print(f"❌ No SPARQL results for {self.message_type}")
                return

            messageData = self._extract_message_data(sparqlResult)
            if not messageData:
                print(f"❌ Error: Could not extract data from {self.message_type} message")
                return

            #print(f"✅ {self.message_type} data received:")
            #for key, value in messageData.items():
            #    print(f"   {key}: {value}")

            # Armazenar dados no agente
            await self.store_data(messageData, msg)
            
            # Verificar regras de negócio
            if hasattr(self.agent, 'verificar_regras_negocio'):
                try:
                    await self.agent.verificar_regras_negocio()
                except Exception as e:
                    print(f"❌ Error in business rules check: {e}")

        except Exception as e:
            print(f"❌ Error processing {self.message_type}: {e}")
            traceback.print_exc()

    def _load_sparql_query(self):
        """Carrega query SPARQL com cache"""
        if self.sparql_filename in self.sparql_cache:
            return self.sparql_cache[self.sparql_filename]
        
        filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sparql", "select", self.sparql_filename))
        
        try:
            if os.path.isfile(filepath):
                with open(filepath, "r", encoding='utf-8') as sparqlFile:
                    query = sparqlFile.read()
                    self.sparql_cache[self.sparql_filename] = query
                    return query
            else:
                print(f"❌ SPARQL file not found: {filepath}")
                return self._create_fallback_query()
        except Exception as e:
            print(f"❌ Error loading SPARQL file {self.sparql_filename}: {e}")
            return self._create_fallback_query()

    def _create_fallback_query(self):
        """Cria query SPARQL básica como fallback"""
        return """
        PREFIX cao: <http://my.campus.org/communicative-acts#>
        
        SELECT ?data WHERE {
            ?s cao:currentConsumption ?consumption .
            ?consumption cao:hasValue ?data .
        }
        """

    def _execute_sparql_query(self, msg, query):
        """Executa query SPARQL e retorna resultado"""
        try:
            if not msg.body:
                print("❌ Message without body")
                return None
            
            graph = rdflib.Graph()
            
            try:
                graph.parse(data=msg.body, format="turtle")
            except Exception as parse_error:
                print(f"❌ Error parsing RDF: {parse_error}")
                try:
                    graph.parse(data=msg.body, format="xml")
                except:
                    print("❌ Could not parse message in any known RDF format")
                    return None
            
            if len(graph) == 0:
                print("❌ Empty RDF graph after parsing")
                return None
            
            sparqlResult = graph.query(query)
            return sparqlResult
            
        except Exception as e:
            print(f"❌ Error executing SPARQL query: {e}")
            return None

    def _extract_message_data(self, sparqlResult):
        """Extrai dados da mensagem do resultado SPARQL"""
        try:
            if len(sparqlResult) == 0:
                print("❌ Empty SPARQL result")
                return None
            
            # Tentar múltiplos métodos de extração
            for row in sparqlResult:
                # Método 1: Mapeamento manual de variáveis
                try:
                    data = {}
                    for i, var in enumerate(sparqlResult.vars):
                        if i < len(row):
                            key = str(var)
                            value = str(row[i])
                            
                            # Tentar parse como JSON se parecer JSON
                            if value.startswith('{') and value.endswith('}'):
                                try:
                                    data.update(json.loads(value))
                                except json.JSONDecodeError:
                                    data[key] = value
                            else:
                                data[key] = value
                    
                    if data:
                        return data
                except Exception:
                    pass
            
            # Fallback: criar estrutura básica de dados
            print("⚠️ Using fallback data extraction")
            return {
                'timestamp': datetime.now().isoformat(),
                'message_type': self.message_type,
                'raw_result_count': len(sparqlResult)
            }
            
        except Exception as e:
            print(f"❌ Error extracting message data: {e}")
            return None

    async def store_data(self, messageData, msg):
        """Armazena dados de consumo no agente"""
        try:
            # Extrair valor numérico do consumo
            consumption_value = self._extract_consumption_value(messageData)
            
            # Armazenar dados completos no agente
            self.agent.ultimo_consumo = {
                'dados_brutos': messageData,
                'valor_consumo': consumption_value,
                'timestamp_recebimento': datetime.now().isoformat(),
                'sender': str(msg.sender),
                'thread': msg.thread,
                'campus_id': getattr(self.agent, 'campus_id', 'unknown'),
                'message_metadata': {
                    'performative': msg.get_metadata("performative"),
                    'ontology': msg.get_metadata("ontology"),
                    'language': msg.get_metadata("language")
                }
            }
            
            # Log detalhado
            #print(f"💾 Consumption data stored from {msg.sender}")
            #print(f"   📋 Raw message data keys: {list(messageData.keys())}")
            if consumption_value is not None:
                pass
                #print(f"   📊 Current consumption: {consumption_value} kW")
            else:
                print(f"   ⚠️ Could not extract numeric consumption value")
                print(f"   🔍 Debug - message data sample: {dict(list(messageData.items())[:5])}")
            
            # Verificar se dados foram armazenados
            if not hasattr(self.agent, 'ultimo_consumo'):
                print(f"   ❌ Failed to store data in agent.ultimo_consumo")
            
            # Adicionar à lista de mensagens recebidas para auditoria
            if not hasattr(self.agent, 'mensagens_recebidas'):
                self.agent.mensagens_recebidas = []
            
            self.agent.mensagens_recebidas.append({
                'tipo': 'CurrentConsumptionInform',
                'timestamp': datetime.now().isoformat(),
                'sender': str(msg.sender),
                'valor': consumption_value
            })
            
        except Exception as e:
            print(f"❌ Error storing consumption data: {e}")
            import traceback
            traceback.print_exc()

    def _extract_consumption_value(self, messageData):
        """Extrai valor numérico de consumo dos dados da mensagem"""
        try:
            # Método 1: Estrutura padrão esperada
            if 'current_consumption' in messageData:
                consumption_data = messageData['current_consumption']
                if isinstance(consumption_data, dict):
                    return float(consumption_data.get('value', 0))
                else:
                    return float(consumption_data)
            
            # Método 2: Chaves alternativas
            elif 'valor' in messageData:
                return float(messageData['valor'])
            elif 'consumption' in messageData:
                return float(messageData['consumption'])
            elif 'value' in messageData:
                return float(messageData['value'])
            
            # Método 3: Dados aninhados em JSON
            elif 'dict' in messageData:
                try:
                    nested_data = json.loads(messageData['dict'])
                    if 'current_consumption' in nested_data:
                        return float(nested_data['current_consumption'].get('value', 0))
                except json.JSONDecodeError:
                    pass
            
            # Método 4: Procurar por qualquer chave que contenha 'consumption'
            for key, value in messageData.items():
                if 'consumption' in key.lower():
                    try:
                        if isinstance(value, dict) and 'value' in value:
                            return float(value['value'])
                        else:
                            return float(value)
                    except (ValueError, TypeError):
                        continue
            
            # Método 5: Fallback - tentar converter qualquer valor numérico
            for key, value in messageData.items():
                try:
                    numeric_value = float(value)
                    print(f"⚠️ Using fallback extraction from key '{key}': {numeric_value}")
                    return numeric_value
                except (ValueError, TypeError):
                    continue
            
            # Se chegou aqui, não conseguiu extrair
            print(f"⚠️ Consumption value extraction failed")
            print(f"   Available keys: {list(messageData.keys())}")
            print(f"   Sample data: {dict(list(messageData.items())[:3])}")
            return None
            
        except Exception as e:
            print(f"❌ Error extracting consumption value: {e}")
            return None

    def _validate_consumption_data(self, messageData):
        """Valida se os dados de consumo são válidos"""
        try:
            consumption_value = self._extract_consumption_value(messageData)
            
            if consumption_value is None:
                return False, "No numeric consumption value found"
            
            if consumption_value < 0:
                return False, f"Negative consumption value: {consumption_value}"
            
            if consumption_value > 1000:  # Assumindo limite máximo de 1000 kW
                return False, f"Consumption value too high: {consumption_value}"
            
            return True, "Valid consumption data"
            
        except Exception as e:
            return False, f"Validation error: {e}"

    def get_status(self):
        """Retorna status atual do processador"""
        return {
            'processor_type': 'ConsumptionInformProcessor',
            'message_type': self.message_type,
            'thread_filter': self.thread_filter,
            'processed_count': self.processed_count,
            'last_consumption': hasattr(self.agent, 'ultimo_consumo') and self.agent.ultimo_consumo is not None
        }

    async def on_end(self):
        print("{} - [{}] - Ending ConsumptionInformProcessor - Processed {} messages".format(
            datetime.now(), self.agent.name, self.processed_count))
        
        # Log final statistics
        if hasattr(self.agent, 'ultimo_consumo') and self.agent.ultimo_consumo:
            last_value = self.agent.ultimo_consumo.get('valor_consumo', 'unknown')
            timestamp = self.agent.ultimo_consumo.get('timestamp_recebimento', 'unknown')
            sender = self.agent.ultimo_consumo.get('sender', 'unknown')
            #print(f"   📊 Last consumption value: {last_value} kW from {sender} at {timestamp}")
        else:
            print(f"   ⚠️ No consumption data received or stored")