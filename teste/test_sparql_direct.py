#!/usr/bin/env python3
"""
Script Python para executar query SPARQL no GraphDB
"""
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import json

def execute_sparql_query():
    # Carregar configurações
    load_dotenv()
    
    graphdb_url = os.getenv('GRAPHDB_URL')
    graphdb_user = os.getenv('GRAPHDB_USER')
    graphdb_password = os.getenv('GRAPHDB_PASSWORD')
    
    # Query SPARQL
    query = """
PREFIX  cao:  <http://my.campus.org/communicative-acts#>
PREFIX  ieso: <https://www.gecad.isep.ipp.pt/ieso/v1.1.0/>
PREFIX  time: <http://www.w3.org/2006/time#>
PREFIX  rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT  ?dict
WHERE
  { _:b0  rdf:type              cao:GenerationForecastInform ;
          cao:generationForecast  _:b1 .
    _:b1  rdf:type              ieso:Prediction ;
          ieso:hasMeasurement   _:b2 .
    _:b2  rdf:type              ieso:Measurement ;
          ieso:hasDateTime      ?measurement_dt ;
          ieso:hasMeasurementValue  _:b3 .
    _:b3  rdf:type              ieso:MeasurementValue ;
          ieso:hasUnitOfMeasure  ?generation_forecast_unit ;
          ieso:hasLiteralValue  ?generation_forecast_value .
    _:b0  time:hasBeginning     _:b4 .
    _:b4  rdf:type              time:Instant ;
          time:inXSDDateTimeStamp  ?has_beggining .
    _:b0  time:hasEnd           _:b5 .
    _:b5  rdf:type              time:Instant ;
          time:inXSDDateTimeStamp  ?has_end .
    _:b0  time:hasTime          _:b6 .
    _:b6  rdf:type              time:Instant ;
          time:inXSDDateTimeStamp  ?dt
    BIND(concat("{\\"message_type\\":\\"GenerationForecastInform\\",\\"generation_forecast\\":{\\"value\\":\\"", str(?generation_forecast_value), "\\",\\"unit\\":\\"", str(?generation_forecast_unit), "\\",\\"timestamp\\":\\"", str(?measurement_dt), "\\"},\\"has_beggining\\":\\"", str(?has_beggining), "\\",\\"has_end\\":\\"", str(?has_end), "\\",\\"timestamp\\":\\"", str(?dt), "\\"}") AS ?dict)
  }
"""
    
    print(f"🔍 Executando query SPARQL...")
    print(f"🌐 GraphDB URL: {graphdb_url}")
    print(f"👤 User: {graphdb_user}")
    
    try:
        headers = {
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json'
        }
        
        response = requests.post(
            graphdb_url,
            data=query,
            headers=headers,
            auth=HTTPBasicAuth(graphdb_user, graphdb_password),
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Query executada com sucesso!")
            print(f"📊 Resultados encontrados: {len(result['results']['bindings'])}")
            
            if result['results']['bindings']:
                print("\n📋 Dados encontrados:")
                for i, binding in enumerate(result['results']['bindings']):
                    print(f"  {i+1}. {binding}")
            else:
                print("\n⚠️ Nenhum dado encontrado com esse padrão")
                print("💡 Isso pode significar que:")
                print("   - Não há mensagens GenerationForecastInform no GraphDB")
                print("   - Os dados estão em formato diferente")
                print("   - A estrutura RDF não corresponde ao padrão da query")
            
            return result
        else:
            print(f"❌ Erro na query. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao executar query: {e}")
        return None

def test_simple_query():
    """Executa uma query simples para testar conectividade"""
    load_dotenv()
    
    graphdb_url = os.getenv('GRAPHDB_URL')
    graphdb_user = os.getenv('GRAPHDB_USER')
    graphdb_password = os.getenv('GRAPHDB_PASSWORD')
    
    # Query simples para contar triplas
    query = """
SELECT (COUNT(*) as ?count)
WHERE { 
    ?s ?p ?o 
}
"""
    
    try:
        headers = {
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json'
        }
        
        response = requests.post(
            graphdb_url,
            data=query,
            headers=headers,
            auth=HTTPBasicAuth(graphdb_user, graphdb_password),
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            count = result['results']['bindings'][0]['count']['value']
            print(f"✅ Conexão OK! Total de triplas no GraphDB: {count}")
            return True
        else:
            print(f"❌ Erro de conexão. Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro de conectividade: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Teste de Query SPARQL no GraphDB\n")
    
    # Teste 1: Conectividade
    print("=" * 50)
    print("TESTE 1: Verificando conectividade")
    connection_ok = test_simple_query()
    
    if connection_ok:
        # Teste 2: Query específica
        print("\n" + "=" * 50)
        print("TESTE 2: Executando query GenerationForecastInform")
        result = execute_sparql_query()
        
        if result:
            print("\n🎉 Query executada com sucesso!")
        else:
            print("\n⚠️ Query falhou")
    else:
        print("\n❌ Problemas de conectividade. Verifique:")
        print("   - Servidor GraphDB está online")
        print("   - Credenciais no arquivo .env")
        print("   - URL do repositório")
