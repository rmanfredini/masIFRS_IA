import json
import os
import rdflib
from datetime import datetime
from peak import Message, OneShotBehaviour
import sys
from dotenv import load_dotenv  
load_dotenv()
CAMPUS_ID = os.getenv('CAMPUS_ID')

util_dir = os.path.join(os.path.dirname(__file__), 'masIFRS_IA', 'util')
sys.path.append(util_dir)
from util.chronosForecaster import ChronosForecaster


class ConsumptionForecastInform(OneShotBehaviour):

  def __init__(self, msg: Message):
    super().__init__()
    self.message = msg
    self.campus = CAMPUS_ID 

  async def on_start(self):
    #print("{} - [{}] - Starting ConsumptionForecastInform . . .".format(datetime.now(), self.agent.name))
    pass

  async def run(self):
    # Get sparql select file 
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sparql", "select", "get-consumption-forecast-request-data.sparql"))
    # DEBUG: print(filepath)

    # if filepath is a file
    if os.path.isfile(filepath):
      # Get file content
      sparqlFile = open(filepath, "r")
      sparqlQuery = sparqlFile.read()
      # DEBUG: print(sparqlQuery)

      # Set empty graph
      graph = rdflib.Graph()
      graph.parse(data = self.message.body, format = "turtle")

      # Get message data
      sparqlResult = graph.query(sparqlQuery)
      if len(sparqlResult) == 1:
        messageData = json.loads(sparqlResult.bindings[0][sparqlResult.vars[0]])

        if messageData["message_type"] == "ConsumptionForecastRequest":
          # Get sparql construct file
          filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sparql", "construct", "consumption-forecast-inform.sparql"))
          # DEBUG: print(filepath)

          # if filepath is a file
          if os.path.isfile(filepath):
            # Get file content
            sparqlFile = open(filepath, "r")
            sparqlTemplate = sparqlFile.read()
            # DEBUG: print(sparqlTemplate)

            sparqlConstruct = sparqlTemplate.replace("<[CONSUMPTION_FORECAST]>", str(self.prever_consumo())).replace("<[MEASUREMENT_DATETIME]>", datetime.now().isoformat()).replace("<[BEGINNING]>", datetime.now().isoformat()).replace("<[END]>", datetime.now().isoformat())
            # DEBUG: print(sparqlConstruct)

            # Reset graph
            graph = rdflib.Graph()
            sparqlResult = graph.query(sparqlConstruct)
            for row in sparqlResult:
              graph.add(row)

            # Get graph content serialized in turtle
            content = graph.serialize(format = "turtle")
            # DEBUG: print(content)

            # Prepare message
            response = self.message.make_reply()
            response.set_metadata("performative", "inform")
            response.set_metadata("ontology", "cao")
            response.set_metadata("language", "turtle")
            response.thread = "consumption-forecast-inform"
            response.body = content
            
            # send message
            await self.send(response)
        else:
          response = self.message.make_reply()
          response.set_metadata("performative", "not-understood")
          response.body = "Unable to solve your {} message".format(self.message.get_metadata("performative"))
          # send message
          await self.send(response)
  
  async def on_end(self):
    pass
    #print("{} - [{}] - Ending ConsumptionForecastInform . . .".format(datetime.now(), self.agent.name))
    
  def prever_consumo(self):
        """
        Previsão de consumo para as próximas horas.
        """
        #print(f'prever_consumo: {self.campus}')
        # Criar instância do forecaster e executar previsão
        forecaster = ChronosForecaster(mode='consumo', campus_id=self.campus, forecast_horizon=4, plot_range=96, plotar=False)
        previsoes_df, erro = forecaster.run_forecast(save_plot=False)
        
        # Extrair apenas o valor mediano da primeira previsão
        valor_previsto = float(previsoes_df['median'].iloc[0])
        
        #print(f'consumo previsto: {valor_previsto}')
        return valor_previsto
    