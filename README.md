# masIFRS
Multi-agent system for controlling photovoltaic power plants using ontology


# execute
peak start mas-ifrs.yaml

# monitor up
cd monitor
uvicorn server:app --host 0.0.0.0 --port 8765 # -> http://localhost:8765