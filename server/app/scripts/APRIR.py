import base64
import json
import requests
from app.pydantic_models.recipes import RecipeFull

class ImageRecipeExtractor:
    def __init__(self, ollama_url: str, model: str):
        self.ollama_url = ollama_url
        self.model = model

    def extract(self, image_bytes: bytes, dish_id: int) -> RecipeFull:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        schema = RecipeFull.model_json_schema()
        
        payload = {
            "model": self.model,
            "prompt": f"Extract recipe for Dish ID {dish_id}",
            "system": f"OCR expert. Output JSON per schema: {json.dumps(schema)}. Rules: 1 egg scale, integer quantities.",
            "stream": False,
            "format": "json",
            "images": [base64_image],
            "options": {"temperature": 0},
            "keep_alive": 0
        }
        
        response = requests.post(self.ollama_url, json=payload)
        response.raise_for_status()
        return RecipeFull.model_validate_json(response.json().get("response"))