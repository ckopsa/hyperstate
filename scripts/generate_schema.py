# scripts/generate_schema.py

import json
from hyperstate.response import HyperStateResponse

schema = HyperStateResponse.model_json_schema()
print(json.dumps(schema, indent=2))
