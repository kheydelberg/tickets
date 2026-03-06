# app/utils/json_encoder.py
import json
from datetime import datetime, date
from uuid import UUID

class CustomJSONEncoder(json.JSONEncoder):
    """Кастомный JSON encoder для обработки datetime и UUID"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)