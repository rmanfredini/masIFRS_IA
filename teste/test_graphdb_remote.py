#!/usr/bin/env python3
"""
Teste de conexão com GraphDB remoto usando credenciais do .env
"""
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

def test_graphdb_connection():
    # Carregar variáveis de ambiente
    load_dotenv()
    
    graphdb_url = os.getenv('GRAPHDB_URL')
    graphdb_user = os.getenv('GRAPHDB_USER') 
    graphdb_password = os.getenv('GRAPHDB_PASSWORD')
    
    print(f"📊 Testing GraphDB connection...")
    print(f"🌐 URL: {graphdb_url}")
    print(f"👤 User: {graphdb_user}")
    print(f"🔒 Password: {'*' * len(graphdb_password) if graphdb_password else 'None'}")
    
    if not all([graphdb_url, graphdb_user, graphdb_password]):
        print("❌ Missing GraphDB credentials in .env file")
        return False
    
    try:
        # Teste simples: fazer uma query SELECT para verificar conexão
        test_query = """
        PREFIX br: <http://my.campus.org/business-rules#>
        SELECT (count(*) as ?count) WHERE { 
            ?s ?p ?o 
        }
        """
        
        headers = {
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json'
        }
        
        response = requests.post(
            f"{graphdb_url}",
            data=test_query,
            headers=headers,
            auth=HTTPBasicAuth(graphdb_user, graphdb_password),
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ GraphDB connection successful!")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ GraphDB connection failed. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_sparql_update():
    # Carregar variáveis de ambiente
    load_dotenv()
    
    graphdb_url = os.getenv('GRAPHDB_URL')
    graphdb_user = os.getenv('GRAPHDB_USER')
    graphdb_password = os.getenv('GRAPHDB_PASSWORD')
    
    # Carregar e processar query de update
    query_path = "agent/coordinator/sparql/update/update-forecast-data.sparql"
    
    if not os.path.exists(query_path):
        print(f"❌ Query file not found: {query_path}")
        return False
    
    with open(query_path, "r", encoding='utf-8') as f:
        query = f.read()
    
    # Valores de teste
    test_consumption = "123.45"
    test_generation = "67.89"
    
    # Substituir placeholders
    query = query.replace("<[consumptionValue]>", test_consumption)
    query = query.replace("<[generationValue]>", test_generation)
    
    print(f"🧪 Testing SPARQL UPDATE with test values:")
    print(f"   Consumption: {test_consumption}")
    print(f"   Generation: {test_generation}")
    
    try:
        headers = {
            'Content-Type': 'application/sparql-update',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            f"{graphdb_url}/statements",
            data=query,
            headers=headers,
            auth=HTTPBasicAuth(graphdb_user, graphdb_password),
            timeout=30
        )
        
        if response.status_code == 204:
            print(f"✅ SPARQL UPDATE successful!")
            return True
        else:
            print(f"❌ SPARQL UPDATE failed. Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during SPARQL UPDATE: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing GraphDB Remote Connection\n")
    
    # Teste 1: Conexão básica
    print("=" * 50)
    print("TEST 1: Basic Connection")
    connection_ok = test_graphdb_connection()
    
    # Teste 2: SPARQL UPDATE (só se conexão funcionar)
    if connection_ok:
        print("\n" + "=" * 50)
        print("TEST 2: SPARQL UPDATE")
        update_ok = test_sparql_update()
        
        if update_ok:
            print("\n🎉 All tests passed! GraphDB integration ready.")
        else:
            print("\n⚠️ Connection works but UPDATE failed.")
    else:
        print("\n❌ Connection failed. Check credentials and network.")
