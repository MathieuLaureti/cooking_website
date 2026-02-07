import json
import httpx # Use httpx for async HTTP requests
import asyncio
import os
from playwright.async_api import async_playwright
from app.pydantic_models.recipes import RecipeFull

class WebRecipeExtractor:
    def __init__(self, ollama_url: str, model: str):
        self.ollama_url = ollama_url
        self.model = model

    async def fetch_text(self, url: str) -> str:
        async with async_playwright() as p:
            # Optimized for ARM/Pi
            browser = await p.chromium.launch(args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--single-process" # Reduces memory footprint on low-end hardware
            ])
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Use a longer timeout but better wait strategy
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Remove script and style tags to clean up the text for the LLM
                await page.evaluate("""() => { 
                    const tags = ["script", "style", "header", "footer", "nav", "aside"];
                    tags.forEach(t => document.querySelectorAll(t).forEach(el => el.remove()));
                }""")

                # Extract text directly from the body
                extracted_text = await page.inner_text("body")
                
                if len(extracted_text.strip()) < 350:
                    raise ValueError("Extracted text too short.")
                    
                return extracted_text
                
            except Exception as e:
                raise ValueError(f"Web extraction failed: {str(e)}")
            finally:
                await browser.close()

    async def extract(self, url: str, dish_id: int) -> RecipeFull:
        text = await self.fetch_text(url)
        schema = RecipeFull.model_json_schema()
        
        payload = {
            "model": self.model,
            "prompt": f"Dish ID: {dish_id}\n\nText:\n{text}",
            "system": f"Professional chef. Output JSON per schema: {json.dumps(schema)}. Rules: quantities are strings to account for (e.g., '1/4', '1/2') else put integer. No accents in title like é for example café should be cafe and reduce it to its simplest form. A Recipe can be a list of ingredient with no instructions.",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_ctx": 8192},
            "keep_alive": 0
        }
        
        # Use httpx for non-blocking I/O
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(self.ollama_url, json=payload)
            response.raise_for_status()
            
        return RecipeFull.model_validate_json(response.json().get("response"))