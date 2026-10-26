import json
import os
import psycopg2
import logging
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

# Configurar logger do peak.database
logger = logging.getLogger("peak.database")
logger.setLevel(logging.INFO)

class dbtransaction:

    def __init__(self):
        self.db_connection = None
        self.conectar_bd()

    def _log_interaction(self, query, params, result=None, error=None):
        escaped_query = " ".join(query.split())
        status = "SUCCESS" if not error else "ERROR"
        details = str(result) if not error else str(error)
        logger.info(
            f"[DB_MSG] PGSQL | Query: {escaped_query} | Params: {params} | Status: {status} | Result: {details}"
        )

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
            logger.info("[DB_MSG] PGSQL | Action: CONNECT | Status: SUCCESS")
        except Exception as e:
            print(f"Database connection error: {e}")
            logger.error(f"[DB_MSG] PGSQL | Action: CONNECT | Status: ERROR | Result: {e}")
    
    def desconectar(self):
        """Fecha conexão com o banco"""
        if self.db_connection:
            self.db_connection.close()
            logger.info("[DB_MSG] PGSQL | Action: DISCONNECT | Status: SUCCESS")

    def obter_consumo_atual(self):
        """
        Obtém a última medição de consumo do campus
        """
        query = "N/A"
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
                val = float(resultado[0])
                self._log_interaction(query, (CAMPUS_ID,), val)
                return val
            else:
                self._log_interaction(query, (CAMPUS_ID,), 0)
                return 0
                
        except Exception as e:
            print(f"Error obtaining current consumption: {e}")
            self._log_interaction(query, (CAMPUS_ID,), error=e)
            return 0

    def obter_geracao_atual(self):
        """
        Obtém a soma das últimas medições de geração por dispositivo no campus
        """
        query = "N/A"
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
                val = float(resultado[0])
                self._log_interaction(query, (campus_id,), val)
                return val
            else:
                self._log_interaction(query, (campus_id,), 0)
                return 0

        except Exception as e:
            print(f"Error obtaining current generation: {e}")
            self._log_interaction(query, (CAMPUS_ID,), error=e)
            return 0

    def obter_capacidade_armazenamento(self):
        """
        Obtém a capacidade total de armazenamento em kWh
        """
        query = "N/A"
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
                val = float(resultado[0])
                self._log_interaction(query, (CAMPUS_ID,), val)
                return val
            else:
                self._log_interaction(query, (CAMPUS_ID,), 100.0)
                return 100.0  # Valor padrão

        except Exception as e:
            print(f"Error obtaining storage capacity: {e}")
            self._log_interaction(query, (CAMPUS_ID,), error=e)
            return 100.0  # Valor padrão

    def obter_carga_armazenamento(self):
        """
        Obtém a carga atual de armazenamento em percentual
        """
        query = "N/A"
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
                val = float(resultado[0])
                self._log_interaction(query, (CAMPUS_ID,), val)
                return val
            else:
                self._log_interaction(query, (CAMPUS_ID,), 75.0)
                return 75.0  # Valor padrão

        except Exception as e:
            print(f"Error obtaining storage charge: {e}")
            self._log_interaction(query, (CAMPUS_ID,), error=e)
            return 75.0  # Valor padrão

    def obter_eficiencia_armazenamento(self):
        """
        Obtém a eficiência do sistema de armazenamento em percentual
        """
        query = "N/A"
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
                val = float(resultado[0])
                self._log_interaction(query, (CAMPUS_ID,), val)
                return val
            else:
                self._log_interaction(query, (CAMPUS_ID,), 90.0)
                return 90.0  # Valor padrão

        except Exception as e:
            print(f"Error obtaining storage efficiency: {e}")
            self._log_interaction(query, (CAMPUS_ID,), error=e)
            return 90.0  # Valor padrão