"""Structured application logs. Credentials and query payloads are intentionally excluded."""
import json
import logging
from datetime import datetime,timezone
class JsonFormatter(logging.Formatter):
    def format(self,record):
        entry={'time':datetime.now(timezone.utc).isoformat(),'level':record.levelname,'event':record.getMessage()}
        for key in ('resource','status'):
            if hasattr(record,key):entry[key]=getattr(record,key)
        return json.dumps(entry,ensure_ascii=False)
def configure():
    log=logging.getLogger('lcm')
    if not log.handlers:
        handler=logging.StreamHandler();handler.setFormatter(JsonFormatter());log.addHandler(handler)
    log.setLevel(logging.INFO);log.propagate=False
