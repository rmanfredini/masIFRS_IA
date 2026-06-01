#!/usr/bin/env python3
"""
Script para explorar que tipos de dados existem no GraphDB
"""
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

def explore_graphdb_data():
    load_dotenv()
    
    graphdb_url = os.getenv('GRAPHDB_URL')
    graphdb_user = os.getenv('GRAPHDB_USER')
    graphdb_password = os.getenv('GRAPHDB_PASSWORD')
    
    # Query para ver tipos de dados existentes
    query = """
PREFIX cao: <http://my.campus.org/communicative-acts#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?type (COUNT(?s) as ?count)
WHERE { 
    ?s rdf:type ?type 
}
GROUP BY ?type
ORDER BY DESC(?count)
"""
    
    print("🔍 Explorando tipos de dados no GraphDB...")
    
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
            print(f"✅ Tipos de dados encontrados: {len(result['results']['bindings'])}")
            print("\n📋 Lista de tipos RDF no GraphDB:")
            
            for binding in result['results']['bindings']:
                type_uri = binding['type']['value']
                count = binding['count']['value']
                print(f"   📊 {count:>4}x {type_uri}")
                
            return result
        else:
            print(f"❌ Erro: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

if __name__ == "__main__":
    explore_graphdb_data()
