from datetime import datetime
from peak import OneShotBehaviour
import json
import rdflib
import os
import traceback

class GenerationInformProcessor(OneShotBehaviour):
    """
    Processa mensagens CurrentGenerationInform do Meter via XMPP direto
    """
    
    def __init__(self, msg=None):
        super().__init__()
        self.message_type = "CurrentGenerationInform"
        self.thread_filter = "current-generation-inform"
        self.sparql_filename = "get-current-generation-inform-data.sparql"
        self.sparql_cache = {}
        self.processed_count = 0
        self.msg = msg

    async def on_start(self):
        #print("{} - [{}] - Starting GenerationInformProcessor for thread '{}' . . .".format(
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
                    #print(f"✅ GenerationInformProcessor processing message from {msg.sender}")
                    await self.process_message(msg)
                    self.processed_count += 1
                # Se não for para este processador, ignora (outros processadores vão tratar)
                    
        except Exception as e:
            print(f"❌ Error in GenerationInformProcessor: {e}")
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
            #    datetime.now(), self.agent.name, self.message_type, msg.sender, msg.thread))
            
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
        
        filepath = os.path.abspath(os.path.join("agent", "coordinator", "sparql", "select", self.sparql_filename))
        
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
            ?s cao:currentGeneration ?Generation .
            ?Generation cao:hasValue ?data .
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
        """Armazena dados de geracao no agente"""
        try:
            # Extrair valor numérico da geracao
            generation_value = self._extract_generation_value(messageData)

            # Armazenar dados completos no agente
            self.agent.ultima_geracao = {  # ← CORRIGIDO
                'dados_brutos': messageData,
                'valor_geracao': generation_value,  # ← CORRIGIDO
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
            #print(f"💾 Generation data stored from {msg.sender}")
            if generation_value is  None:
                print(f"   ⚠️ Could not extract numeric Generation value")
            
            # Adicionar à lista de mensagens recebidas para auditoria
            if hasattr(self.agent, 'mensagens_recebidas'):
                self.agent.mensagens_recebidas.append({
                    'tipo': 'CurrentGenerationInform',
                    'timestamp': datetime.now().isoformat(),
                    'sender': str(msg.sender),
                    'valor': generation_value
                })
            
        except Exception as e:
            print(f"❌ Error storing Generation data: {e}")

    def _extract_generation_value(self, messageData):
        """Extrai valor numérico de geracao dos dados da mensagem"""
        try:
            # Método 1: Estrutura padrão esperada
            if 'current_generation' in messageData:
                generation_data = messageData['current_generation']
                if isinstance(generation_data, dict):
                    return float(generation_data.get('value', 0))
                else:
                    return float(generation_data)

            # Método 2: Chaves alternativas
            elif 'valor' in messageData:
                return float(messageData['valor'])
            elif 'Generation' in messageData:
                return float(messageData['Generation'])
            elif 'value' in messageData:
                return float(messageData['value'])
            
            # Método 3: Dados aninhados em JSON
            elif 'dict' in messageData:
                try:
                    nested_data = json.loads(messageData['dict'])
                    if 'current_Generation' in nested_data:
                        return float(nested_data['current_Generation'].get('value', 0))
                except json.JSONDecodeError:
                    pass
            
            # Método 4: Procurar por qualquer chave que contenha 'Generation'
            for key, value in messageData.items():
                if 'generation' in key.lower():
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
            print(f"⚠️ Generation value extraction failed")
            print(f"   Available keys: {list(messageData.keys())}")
            print(f"   Sample data: {dict(list(messageData.items())[:3])}")
            return None
            
        except Exception as e:
            print(f"❌ Error extracting Generation value: {e}")
            return None

    def _validate_generation_data(self, messageData):
        """Valida se os dados de geracao são válidos"""
        try:
            generation_value = self._extract_generation_value(messageData)

            if generation_value is None:
                return False, "No numeric Generation value found"
            
            if generation_value < 0:
                return False, f"Negative Generation value: {generation_value}"

            if generation_value > 1000:  # Assumindo limite máximo de 1000 kW
                return False, f"Generation value too high: {generation_value}"

            return True, "Valid Generation data"
            
        except Exception as e:
            return False, f"Validation error: {e}"

    def get_status(self):
        """Retorna status atual do processador"""
        return {
            'processor_type': 'GenerationInformProcessor',
            'message_type': self.message_type,
            'thread_filter': self.thread_filter,
            'processed_count': self.processed_count,
            'last_generation': getattr(self.agent, 'ultima_geracao', None) is not None
        }

    async def on_end(self):
        print("{} - [{}] - Ending GenerationInformProcessor - Processed {} messages".format(
            datetime.now(), self.agent.name, self.processed_count))
        
        # Log final statistics
        if hasattr(self.agent, 'ultima_geracao') and self.agent.ultima_geracao:
            last_value = self.agent.ultima_geracao.get('valor_geracao', 'unknown')
            timestamp = self.agent.ultima_geracao.get('timestamp_recebimento', 'unknown')
            sender = self.agent.ultima_geracao.get('sender', 'unknown')
            print(f"   📊 Last Generation value: {last_value} kW from {sender} at {timestamp}")
        else:
            print(f"   ⚠️ No Generation data received or stored")