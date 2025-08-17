"""
Document analysis service for mechanical integrity inspection reports.

Uses local Ollama LLM to extract structured data from inspection documents
while maintaining data privacy for sensitive petroleum industry information.
"""
import json
import logging
from typing import Dict, Any, Optional, List

import httpx
from pydantic import BaseModel, Field

from core.config import settings

logger = logging.getLogger(__name__)


class ThicknessMeasurement(BaseModel):
    """Thickness measurement data extracted from inspection reports."""
    location: str = Field(..., description="Measurement location on equipment")
    thickness: float = Field(..., description="Measured thickness in inches")
    measurement_method: Optional[str] = Field(None, description="UT, RT, etc.")


class InspectionData(BaseModel):
    """Structured inspection data extracted from documents."""
    equipment_tag: Optional[str] = Field(None, description="Equipment identifier")
    inspection_date: Optional[str] = Field(None, description="Date of inspection")
    thickness_measurements: List[ThicknessMeasurement] = Field(
        default_factory=list,
        description="All thickness measurements"
    )
    corrosion_rates: List[float] = Field(
        default_factory=list,
        description="Corrosion rates in inches/year"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Inspector recommendations"
    )
    confidence_score: Optional[float] = Field(
        None,
        description="AI extraction confidence (0-1)"
    )


class DocumentAnalyzer:
    """
    AI-powered document analyzer for mechanical integrity inspection reports.
    
    Extracts structured data using local Ollama LLM to maintain data privacy
    for sensitive petroleum industry documents.
    """
    
    def __init__(self) -> None:
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.model_name = settings.OLLAMA_MODEL
        self.timeout = httpx.Timeout(60.0)  # 60 second timeout for AI processing
    
    async def extract_inspection_data(self, document_text: str) -> InspectionData:
        """
        Extract structured inspection data from document text.
        
        Args:
            document_text: Raw text content from inspection document
            
        Returns:
            InspectionData: Structured inspection information
            
        Raises:
            ValueError: If document text is empty or invalid
            httpx.HTTPError: If Ollama service is unavailable
        """
        if not document_text or not document_text.strip():
            raise ValueError("Document text cannot be empty")
        
        logger.info(f"Extracting inspection data from {len(document_text)} characters")
        
        extraction_prompt = self._build_extraction_prompt(document_text)
        
        try:
            raw_response = await self._query_ollama(extraction_prompt)
            extracted_data = self._parse_extraction_response(raw_response)
            
            logger.info(f"Successfully extracted data for equipment: {extracted_data.equipment_tag}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to extract inspection data: {e}")
            # Return empty structure rather than failing completely
            return InspectionData()
    
    def _build_extraction_prompt(self, document_text: str) -> str:
        """Build structured prompt for LLM extraction."""
        return f"""
You are an expert mechanical integrity engineer analyzing an inspection report.
Extract the following information with high precision for API 579 compliance:

CRITICAL SAFETY NOTE: Thickness measurements and corrosion rates are used for 
safety-critical calculations. Be extremely careful with numerical values.

Extract:
1. Equipment Tag/ID (e.g., V-101, T-201, P-301)
2. Inspection Date (any date format)
3. Thickness Measurements:
   - Location description
   - Thickness value in inches (convert if needed)
   - Measurement method if mentioned (UT, RT, etc.)
4. Corrosion Rates (inches/year if mentioned)
5. Inspector Recommendations (verbatim)

Return ONLY valid JSON in this exact format:
{{
    "equipment_tag": "string or null",
    "inspection_date": "string or null", 
    "thickness_measurements": [
        {{"location": "string", "thickness": number, "measurement_method": "string or null"}}
    ],
    "corrosion_rates": [number],
    "recommendations": ["string"],
    "confidence_score": number_between_0_and_1
}}

Document to analyze:
{document_text[:2000]}...
"""
    
    async def _query_ollama(self, prompt: str) -> Dict[str, Any]:
        """Send query to Ollama service with error handling."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": 0.1,  # Low temperature for consistent extraction
                            "top_p": 0.9,
                            "num_predict": 1000
                        }
                    }
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.TimeoutException:
                logger.error("Ollama service timeout")
                raise
            except httpx.HTTPError as e:
                logger.error(f"Ollama service error: {e}")
                raise
    
    def _parse_extraction_response(self, ollama_response: Dict[str, Any]) -> InspectionData:
        """Parse Ollama response into structured data."""
        try:
            # Extract the response text from Ollama format
            response_text = ollama_response.get("response", "")
            if not response_text:
                logger.warning("Empty response from Ollama")
                return InspectionData()
            
            # Parse JSON response
            extracted_json = json.loads(response_text)
            
            # Validate and convert to InspectionData
            return InspectionData.model_validate(extracted_json)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return InspectionData()
        except Exception as e:
            logger.error(f"Error parsing extraction response: {e}")
            return InspectionData()
