import os
import psycopg2
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
import logging
from dotenv import load_dotenv
from chronos import ChronosPipeline

# Configurar logger do peak.database
logger = logging.getLogger("peak.database")
logger.setLevel(logging.INFO)


class ChronosForecaster:
    """
    Classe para previsões usando Amazon Chronos.
    Pode ser configurada para previsão de geração ou consumo (DB: 'geracoes' ou 'consumos').
    """

    def __init__(self, mode='geracao', campus_id=1, forecast_horizon=4, plot_range=96, plotar=False):
        """
        :param mode: 'geracao' ou 'consumo'
        :param campus_id: ID do campus no banco
        :param forecast_horizon: número de horas futuras a prever
        :param plot_range: quantas observações finais serão plotadas no histórico
        """
        load_dotenv()
        self.mode = mode
        self.campus_id = campus_id
        self.forecast_horizon = forecast_horizon
        self.plot_range = plot_range
        self.plotar = plotar

        self.db_config = {
            'host': os.getenv('SERVIDOR_POSTGRESQL'),
            'database': os.getenv('POSTGRESQL_DATABASE'),
            'user': os.getenv('POSTGRESQL_USER'),
            'password': os.getenv('POSTGRESQL_PASSWORD'),
            'port': os.getenv('SERVIDOR_POSTGRESQL_PORTA')
        }

        # Define consulta SQL conforme o modo
        if self.mode == 'consumo':
            #print("Modo de previsão: Consumo (incluindo geração)")
            self.sql_query = f"""
                SELECT 
                    c.timestamp, 
                    GREATEST(0, c.valor_kw + COALESCE(g.potenciagerada_kw, 0)) AS valor
                FROM consumos c
                LEFT JOIN geracoes g ON c.timestamp = g.timestamp 
                    AND c.campus_id = g.campus_id
                WHERE c.campus_id = {self.campus_id}  
                ORDER BY c.timestamp
            """
            self.ylabel = "Consumo + Geração (kW)"
            self.title = "Previsão de Consumo (com Geração)"
        else:
            #print("Modo de previsão: Geração")
            self.sql_query = f"""
                SELECT timestamp, potenciagerada_kw AS valor
                FROM geracoes
                WHERE campus_id = {self.campus_id}  
                ORDER BY timestamp
            """
            self.ylabel = "Potência Gerada (W)"
            self.title = "Previsão de Geração"

    def _mape(self, actual, predicted):
        """Calcula o MAPE ignorando valores zero."""
        mask = actual != 0
        if not np.any(mask):
            return np.nan
        return np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100

    def load_data(self):
        """Carrega dados do banco e retorna DataFrame com colunas [timestamp, valor]."""
        try:
            conn = psycopg2.connect(**self.db_config)
            df = pd.read_sql(self.sql_query, conn)
            conn.close()
            
            escaped_query = " ".join(self.sql_query.split())
            logger.info(
                f"[DB_MSG] PGSQL | Query: {escaped_query} | Params: None | Status: SUCCESS | Result: {len(df)} rows"
            )
            return df
        except Exception as e:
            escaped_query = " ".join(self.sql_query.split())
            logger.error(
                f"[DB_MSG] PGSQL | Query: {escaped_query} | Params: None | Status: ERROR | Result: {e}"
            )
            raise e

    def run_forecast(self, save_plot=False, plot_filename="chronos_forecast.png"):
        """
        Executa o fluxo de previsão com Chronos para as próximas forecast_horizon horas.
        :param save_plot: se True, salva gráfico em plot_filename
        :param plot_filename: nome do arquivo PNG de saída
        :return: (forecast_df, mape_value) com DataFrame das previsões e valor de MAPE
        """
        df = self.load_data()

        # Converter timestamp para UTC e remover tzinfo para compatibilidade com pandas
        dates = pd.to_datetime(df["timestamp"], utc=True, errors='coerce').dt.tz_localize(None)
        series = df["valor"].values

        # Remover linhas com timestamp inválido (NaT)
        valid_mask = ~dates.isna()
        n_invalid = (~valid_mask).sum()
        if n_invalid > 0:
            logger.warning(f"[ChronosForecaster] {n_invalid} registro(s) com timestamp inválido (NaT) removidos antes da previsão.")
        dates = dates[valid_mask].reset_index(drop=True)
        series = series[valid_mask]

        if len(dates) == 0:
            raise ValueError(
                f"[ChronosForecaster] Nenhum dado válido encontrado no banco para mode='{self.mode}', "
                f"campus_id={self.campus_id}. Verifique se há registros com timestamps válidos na tabela."
            )

        # Carregar  modelo
        pipeline = ChronosPipeline.from_pretrained(
            "amazon/chronos-t5-large",
            device_map="auto",
            torch_dtype=torch.bfloat16,
            ignore_mismatched_sizes=True
        )

        # Realizar previsão
        context = torch.tensor(series, dtype=torch.float32).unsqueeze(0)
        forecast_tensor = pipeline.predict(context, self.forecast_horizon)  
        low, median, high = np.quantile(forecast_tensor[0].numpy(), [0.1, 0.5, 0.9], axis=0)

        # Garantir que previsões não fiquem negativas (útil para geração)
        low = np.maximum(low, 0)
        median = np.maximum(median, 0)
        high = np.maximum(high, 0)

        # Criar datas para a previsão
        last_date = dates.iloc[-1]
        if pd.isna(last_date):
            raise ValueError(
                f"[ChronosForecaster] Último timestamp é NaT para mode='{self.mode}'. "
                "Não é possível calcular datas futuras."
            )
        forecast_dates  = pd.date_range(
            start=last_date + pd.Timedelta(hours=1), 
            periods=self.forecast_horizon, 
            freq='h'
        )
        if self.plotar:
            # Selecionar dados históricos recentes para plotagem
            plot_series = series[-self.plot_range:]  
            plot_dates = dates.iloc[-self.plot_range:]

        # Calcular MAPE (comparando toda a série vs. mediana)
        # Caso deseje MAPE somente em parte do histórico, ajuste aqui.
        # Calcular MAPE (comparando as últimas 4 amostras do histórico com as 4 previsões)
        actual_subset = series[-self.forecast_horizon:]
        error = self._mape(actual_subset, median)

        # Plot
        if self.plotar:
            plt.figure(figsize=(10, 5))
            plt.plot(plot_dates, plot_series, color="black", label="Histórico")
            plt.plot(forecast_dates, median, color="red", linestyle="dashed", label="Previsão (Mediana)")
            plt.fill_between(forecast_dates, low, high, color="red", alpha=0.3, label="Intervalo 80%")
            plt.xticks(rotation=45)
            plt.title(self.title)
            plt.ylabel(self.ylabel)
            plt.legend(frameon=False)

            if save_plot:
                plt.savefig(plot_filename)
            plt.show()

        # Preparar DataFrame para retorno
        forecast_df = pd.DataFrame({
            'timestamp': forecast_dates,
            'low': low,
            'median': median,
            'high': high
        })

        return forecast_df, error
    
def main():
    # Exemplo de uso
    #forecaster = ChronosForecaster(mode='geracao', campus_id=1, forecast_horizon=4)
    #forecast_df, error = forecaster.run_forecast(save_plot=True, plot_filename="forecast.png")
    #print(forecast_df)
    #print("MAPE:", error)
    forecaster = ChronosForecaster(mode='consumo', campus_id=1, forecast_horizon=1, plotar=True)
    forecast_df, error = forecaster.run_forecast(save_plot=True, plot_filename="forecast.png")
    print(forecast_df)
    print("MAPE:", error)
    forecaster = ChronosForecaster(mode='geracao', campus_id=1, forecast_horizon=1, plotar=True)
    forecast_df, error = forecaster.run_forecast(save_plot=True, plot_filename="forecast.png")
    print(forecast_df)
    print("MAPE:", error)

    
if __name__ == "__main__":
    main()
