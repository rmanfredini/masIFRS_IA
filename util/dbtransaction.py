import json
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
CAMPUS_ID = os.getenv('CAMPUS_ID')
SERVIDOR_ONTOLOGIA = os.getenv('SERVIDOR_ONTOLOGIA')    
SERVIDOR_POSTGRESQL=os.getenv('SERVIDOR_POSTGRESQL')    
SERVIDOR_POSTGRESQL_PORTA=os.getenv('SERVIDOR_POSTGRESQL_PORTA')
POSTGRESQL_USER=os.getenv('POSTGRESQL_USER')
POSTGRESQL_PASSWORD=os.getenv('POSTGRESQL_PASSWORD')
POSTGRESQL_DATABASE=os.getenv('POSTGRESQL_DATABASE')
SERVIDOR_NOMES=os.getenv('SERVIDOR_NOMES')
SERVIDOR_NOMES_PORTA=os.getenv('SERVIDOR_NOMES_PORTA')

class dbtransaction:

    def __init__(self):
        self.db_connection = None
        self.conectar_bd()

    def conectar_bd(self):
        """Conecta ao banco de dados PostgreSQL"""
        try:
            self.db_connection = psycopg2.connect(
                dbname=POSTGRESQL_DATABASE,
                user=POSTGRESQL_USER,
                password=POSTGRESQL_PASSWORD,
                host=SERVIDOR_POSTGRESQL,
                port=SERVIDOR_POSTGRESQL_PORTA
            )
            #print("{} - [{}] - Database connection established. . . .".format(datetime.now(), "dbtransaction"))
        except Exception as e:
            print(f"Database connection error: {e}")
    
    def desconectar(self):
        """Fecha conexão com o banco"""
        if self.db_connection:
            self.db_connection.close()

    def obter_consumo_atual(self):
        """
        Obtém a última medição de consumo do campus
        """
        try:                
            if not self.db_connection or self.db_connection.closed:
                self.conectar_bd()
                
            cursor = self.db_connection.cursor()
            
            # Query para obter a última medição de consumo do campus
            query = """
            SELECT valor_kw
            FROM consumos 
            WHERE campus_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """

            cursor.execute(query, (CAMPUS_ID,))
            resultado = cursor.fetchone()
            cursor.close()
            self.desconectar()
            
            if resultado:
                return float(resultado[0])
            else:
                return 0
                
        except Exception as e:
            print(f"Error obtaining current consumption: {e}")
            return 0

    def obter_geracao_atual(self):
        """
        Obtém a soma das últimas medições de geração por dispositivo no campus
        """
        try:
            campus_id = CAMPUS_ID
            if not campus_id:
                return 0

            if not self.db_connection or self.db_connection.closed:
                self.conectar_bd()

            cursor = self.db_connection.cursor()

            # Query para obter a última medição de cada dispositivo e somar
            query = """
            WITH ultimas_medicoes AS (
                SELECT
                    dispositivo_id,
                    potenciagerada_kw,
                    ROW_NUMBER() OVER (PARTITION BY dispositivo_id ORDER BY timestamp DESC) as rn
                FROM geracoes
                WHERE campus_id = %s
            )
            SELECT COALESCE(SUM(potenciagerada_kw), 0) as total_geracao
            FROM ultimas_medicoes
            WHERE rn = 1
            """

            cursor.execute(query, (campus_id,))
            resultado = cursor.fetchone()
            cursor.close()
            if resultado:
                return float(resultado[0])
            else:
                return 0

        except Exception as e:
            print(f"Error obtaining current generation: {e}")
            return 0

    def obter_capacidade_armazenamento(self):
        """
        Obtém a capacidade total de armazenamento em kWh
        """
        try:
            if not self.db_connection or self.db_connection.closed:
                self.conectar_bd()
                
            cursor = self.db_connection.cursor()
            
            # Query para obter capacidade de armazenamento
            query = """
            SELECT COALESCE(SUM(capacidade_kwh), 100.0) as capacidade_total
            FROM baterias 
            WHERE campus_id = %s AND ativo = true
            """
            
            cursor.execute(query, (CAMPUS_ID,))
            resultado = cursor.fetchone()
            cursor.close()
            if resultado:
                return float(resultado[0])
            else:
                return 100.0  # Valor padrão

        except Exception as e:
            print(f"Error obtaining storage capacity: {e}")
            return 100.0  # Valor padrão

    def obter_carga_armazenamento(self):
        """
        Obtém a carga atual de armazenamento em percentual
        """
        try:
            if not self.db_connection or self.db_connection.closed:
                self.conectar_bd()
                
            cursor = self.db_connection.cursor()
            
            # Query para obter carga atual
            query = """
            SELECT COALESCE(AVG(carga_percentual), 75.0) as carga_media
            FROM baterias 
            WHERE campus_id = %s AND ativo = true
            """
            
            cursor.execute(query, (CAMPUS_ID,))
            resultado = cursor.fetchone()
            cursor.close()
            if resultado:
                return float(resultado[0])
            else:
                return 75.0  # Valor padrão

        except Exception as e:
            print(f"Error obtaining storage charge: {e}")
            return 75.0  # Valor padrão

    def obter_eficiencia_armazenamento(self):
        """
        Obtém a eficiência do sistema de armazenamento em percentual
        """
        try:
            if not self.db_connection or self.db_connection.closed:
                self.conectar_bd()
                
            cursor = self.db_connection.cursor()
            
            # Query para obter eficiência
            query = """
            SELECT COALESCE(AVG(eficiencia_percentual), 90.0) as eficiencia_media
            FROM baterias 
            WHERE campus_id = %s AND ativo = true
            """
            
            cursor.execute(query, (CAMPUS_ID,))
            resultado = cursor.fetchone()
            cursor.close()
            if resultado:
                return float(resultado[0])
            else:
                return 90.0  # Valor padrão

        except Exception as e:
            print(f"Error obtaining storage efficiency: {e}")
            return 90.0  # Valor padrão