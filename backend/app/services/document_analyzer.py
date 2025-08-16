# backend/app/services/document_analyzer.py
import httpx
from app.core.config import settings

class DocumentAnalyzer:
    def __init__(self):
        self.ollama_url = settings.OLLAMA_API_BASE
        self.model = settings.OLLAMA_MODEL
    
    async def extract_inspection_data(self, document_text: str):
        """Extract structured data from inspection reports using LLaMA"""
        
        prompt = f"""
        You are analyzing a mechanical integrity inspection report.
        Extract the following information:
        - Equipment ID/Tag
        - Inspection Date
        - Thickness measurements (list all)
        - Corrosion rates
        - Any recommendations
        
        Document:
        {document_text}
        
        Return as JSON format.
        """
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False
                }
            )
            return response.json()
