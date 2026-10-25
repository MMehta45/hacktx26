import os

# Tests are deterministic and must never call optional external integrations merely
# because a developer has configured their ignored local environment.
os.environ["DEMO_DATA_MODE"] = "fixture"
os.environ["NESSIE_API_KEY"] = ""
os.environ["SERPAPI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
