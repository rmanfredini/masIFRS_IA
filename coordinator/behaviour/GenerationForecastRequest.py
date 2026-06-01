import os
import rdflib
from datetime import datetime
from peak import Message, OneShotBehaviour

class GenerationForecastRequest(OneShotBehaviour):

  async def on_start(self):
    #print("{} - [{}] - Starting GenerationForecastRequest . . .".format(datetime.now(), self.agent.name))
    pass

  async def run(self):
    # Get sparql construct file
    filepath = os.path.abspath(os.path.join("agent", "coordinator", "sparql", "construct", "generation-forecast-request.sparql"))
    # DEBUG: print(filepath)

    # if filepath is a file
    if os.path.isfile(filepath):
      # Get file content
      sparqlFile = open(filepath, "r")
      sparqlQuery = sparqlFile.read()
      # DEBUG: print(sparqlQuery)

      # Set empty graph
      graph = rdflib.Graph()
      
      # Get/Set message body
      sparqlResult = graph.query(sparqlQuery)
      for row in sparqlResult:
        graph.add(row)
      
      # Get graph content serialized in turtle
      content = graph.serialize(format = "turtle")
      # DEBUG: print(content)

      # Prepare message
      msg = Message()
      msg.to = "predictor@localhost/main"
      msg.set_metadata("performative", "request")
      msg.set_metadata("ontology", "cao")
      msg.set_metadata("language", "turtle")
      msg.thread = "generation-forecast-request"
      msg.body = content
      
      # send message
      await self.send(msg)

    else:
      print("Error: File not found!\nThe filepath {} is invalid.".format(filepath))

  async def on_end(self):
    print("{} - [{}] - Ending GenerationForecastRequest . . .".format(datetime.now(), self.agent.name))