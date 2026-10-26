import json
import os
import rdflib
from datetime import datetime
from peak import Message, OneShotBehaviour
from dotenv import load_dotenv
import sys
import asyncio

# Add the util directory to Python path
util_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'util'))
sys.path.insert(0, util_dir)
from util.dbtransaction import dbtransaction

class CurrentConsumptionInform(OneShotBehaviour):

  def __init__(self, msg: Message):
    super().__init__()
    self.message = msg
    self.db = dbtransaction()

  async def on_start(self):
    #print("{} - [{}] - Starting CurrentConsumptionInform . . .".format(datetime.now(), self.agent.name))
    pass

  async def run(self):
    # Get sparql select file 
    filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sparql", "select", "get-current-consumption-request-data.sparql"))
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

        if messageData["message_type"] == "CurrentConsumptionRequest":
          # Get sparql construct file
          filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sparql", "construct", "current-consumption-inform.sparql"))
          # DEBUG: print(filepath)

          # if filepath is a file
          if os.path.isfile(filepath):
            # Get file content
            sparqlFile = open(filepath, "r")
            sparqlTemplate = sparqlFile.read()
            # DEBUG: print(sparqlTemplate)
            try:
                consumo_atual = await asyncio.to_thread(self.db.obter_consumo_atual)
               # print(f"{datetime.now()} - [{self.agent.name}] - 📊 Current consumption: {consumo_atual} kW")
            except Exception as db_error:
                print(f"{datetime.now()} - [{self.agent.name}] - ⚠️ Database error: {db_error}, using default value")
                consumo_atual = 50.0  # Default value

            sparqlConstruct = sparqlTemplate.replace("<[CONSUMPTION]>", str(consumo_atual)).replace("<[MEASUREMENT_DATETIME]>", datetime.now().isoformat()).replace("<[BEGINNING]>", datetime.now().isoformat()).replace("<[END]>", datetime.now().isoformat())
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
            response.thread = "current-consumption-inform"
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
    #print("{} - [{}] - Ending CurrentConsumptionInform . . .".format(datetime.now(), self.agent.name))
    pass