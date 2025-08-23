"""
Document analysis service for mechanical integrity inspection reports.

Uses local Ollama LLM to extract structured data from inspection documents
while maintaining data privacy for sensitive petroleum industry information.
"""
import json
import logging
import re
from typing import Dict, Any, Optional, List

import httpx
from pydantic import BaseModel, Field

from core.config import settings

logger = logging.getLogger(__name__)


# ========================================================================
# SECURITY PATTERNS AND CONSTANTS
# ========================================================================

# Common malicious patterns to detect in all input sanitization
SECURITY_PATTERNS = {
    'injection_chars': r'[<>"\'\(\);]',  # HTML/SQL injection characters  
    'hex_encoded': r'\\x[0-9a-fA-F]{2}',  # Hex-encoded characters
    'url_encoded': r'%[0-9a-fA-F]{2}',  # URL-encoded characters
    'backslash_escapes': r'\\\w+',  # Backslash escapes
    'variable_interpolation': r'\$\{.*\}',  # Variable interpolation
    'script_tags': r'<script[^>]*>.*?</script>',  # Script tags
    'sql_keywords': r'\b(DROP|DELETE|INSERT|UPDATE|SELECT|UNION|ALTER)\b',  # SQL keywords
}


def _check_security_patterns(text: str, context: str) -> bool:
    """
    Check text against common malicious patterns.
    
    Args:
        text: Text to validate
        context: Context for logging (e.g., 'equipment tag', 'location')
        
    Returns:
        True if safe, False if malicious patterns detected
    """
    for pattern_name, pattern in SECURITY_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            logger.error(f"Malicious pattern '{pattern_name}' detected in {context}: {text[:50]}...")
            return False
    return True


def sanitize_equipment_tag(tag: str) -> Optional[str]:
    """
    Sanitize and validate equipment tag names for security.
    
    Valid equipment tag formats for petroleum industry:
    - V-101 (Vessel)
    - T-201 (Tank) 
    - P-301 (Pump/Piping)
    - E-401 (Heat Exchanger)
    - V-101-SUFFIX (with descriptive suffix)
    
    Args:
        tag: Raw equipment tag from AI extraction
        
    Returns:
        Sanitized tag if valid, None if invalid/malicious
    """
    if not tag or not isinstance(tag, str):
        return None
    
    # Remove any leading/trailing whitespace
    tag = tag.strip()
    
    # Length validation - prevent excessively long tags
    if len(tag) > 50:  # Matches database column limit
        logger.warning(f"Equipment tag too long: {len(tag)} chars")
        return None
    
    # Pattern validation for standard petroleum industry equipment tags
    # Allows: Letter-Number, Letter-Number-Alphanumeric suffix
    equipment_tag_pattern = re.compile(
        r'^[A-Z]{1,3}-\d{1,4}(?:-[A-Z0-9_-]{1,20})?$',
        re.IGNORECASE
    )
    
    if not equipment_tag_pattern.match(tag):
        logger.warning(f"Invalid equipment tag format: {tag}")
        return None
    
    # Convert to uppercase for consistency
    sanitized = tag.upper()
    
    # Security validation using centralized patterns
    if not _check_security_patterns(sanitized, "equipment tag"):
        return None
    
    return sanitized


def sanitize_measurement_location(location: str) -> Optional[str]:
    """
    Sanitize thickness measurement location descriptions.
    
    Args:
        location: Raw location description from AI extraction
        
    Returns:
        Sanitized location if valid, None if invalid
    """
    if not location or not isinstance(location, str):
        return None
        
    # Remove leading/trailing whitespace
    location = location.strip()
    
    # Length validation
    if len(location) > 200:  # Reasonable limit for location descriptions
        return None
    
    # Remove potentially dangerous characters but allow normal punctuation
    # Allow letters, numbers, spaces, hyphens, periods, commas, parentheses
    safe_location = re.sub(r'[^a-zA-Z0-9\s\-\.,\(\)\/]', '', location)
    
    return safe_location if safe_location else None


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
    # TODO: [FEATURE] Add OCR capability for scanned inspection reports
    # Integrate pytesseract or similar for image-based document processing
    # TODO: [VALIDATION] Implement thickness measurement validation against API 579 limits
    # Cross-check extracted values against acceptable ranges for equipment type
    
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
            # TODO: [ENHANCEMENT] Add fallback extraction methods for critical data
            # Implement regex patterns for common thickness measurement formats
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
        """Parse Ollama response into structured data with security validation."""
        try:
            # Extract the response text from Ollama format
            response_text = ollama_response.get("response", "")
            if not response_text:
                logger.warning("Empty response from Ollama")
                return InspectionData()
            
            # Parse JSON response
            extracted_json = json.loads(response_text)
            
            # Apply security sanitization to extracted data
            sanitized_data = self._sanitize_extracted_data(extracted_json)
            
            # Validate and convert to InspectionData
            return InspectionData.model_validate(sanitized_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return InspectionData()
        except Exception as e:
            logger.error(f"Error parsing extraction response: {e}")
            return InspectionData()
    
    def _sanitize_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize extracted data for security and data integrity.
        
        Args:
            data: Raw extracted data from AI
            
        Returns:
            Sanitized data dictionary
        """
        sanitized = data.copy()
        
        # Sanitize equipment tag
        if "equipment_tag" in sanitized and sanitized["equipment_tag"]:
            sanitized_tag = sanitize_equipment_tag(sanitized["equipment_tag"])
            if sanitized_tag:
                sanitized["equipment_tag"] = sanitized_tag
                logger.info(f"Sanitized equipment tag: {sanitized['equipment_tag']}")
            else:
                logger.warning(f"Rejected invalid equipment tag: {sanitized['equipment_tag']}")
                sanitized["equipment_tag"] = None
        
        # Sanitize thickness measurements
        if "thickness_measurements" in sanitized and isinstance(sanitized["thickness_measurements"], list):
            sanitized_measurements = []
            for measurement in sanitized["thickness_measurements"]:
                if isinstance(measurement, dict):
                    sanitized_measurement = measurement.copy()
                    
                    # Sanitize measurement location
                    if "location" in sanitized_measurement:
                        safe_location = sanitize_measurement_location(sanitized_measurement["location"])
                        if safe_location:
                            sanitized_measurement["location"] = safe_location
                        else:
                            logger.warning(f"Rejected invalid measurement location: {sanitized_measurement.get('location')}")
                            continue  # Skip this measurement
                    
                    # Validate thickness value is reasonable
                    if "thickness" in sanitized_measurement:
                        thickness = sanitized_measurement["thickness"]
                        try:
                            thickness_float = float(thickness)
                            # Reasonable thickness range for petroleum equipment: 0.001 to 10 inches
                            if 0.001 <= thickness_float <= 10.0:
                                sanitized_measurement["thickness"] = thickness_float
                            else:
                                logger.warning(f"Thickness value out of range: {thickness}")
                                continue  # Skip this measurement
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid thickness value: {thickness}")
                            continue  # Skip this measurement
                    
                    sanitized_measurements.append(sanitized_measurement)
            
            sanitized["thickness_measurements"] = sanitized_measurements
        
        # Sanitize corrosion rates
        if "corrosion_rates" in sanitized and isinstance(sanitized["corrosion_rates"], list):
            sanitized_rates = []
            for rate in sanitized["corrosion_rates"]:
                try:
                    rate_float = float(rate)
                    # Reasonable corrosion rate range: 0 to 1 inch/year
                    if 0.0 <= rate_float <= 1.0:
                        sanitized_rates.append(rate_float)
                    else:
                        logger.warning(f"Corrosion rate out of range: {rate}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid corrosion rate: {rate}")
            
            sanitized["corrosion_rates"] = sanitized_rates
        
        # Sanitize recommendations (limit length, remove dangerous content)
        if "recommendations" in sanitized and isinstance(sanitized["recommendations"], list):
            sanitized_recommendations = []
            for rec in sanitized["recommendations"]:
                if isinstance(rec, str) and len(rec.strip()) > 0:
                    # Limit length and sanitize content
                    clean_rec = rec.strip()[:500]  # Max 500 chars per recommendation
                    # Remove potentially dangerous patterns
                    clean_rec = re.sub(r'[<>"\'\(\);\\]', '', clean_rec)
                    if clean_rec:
                        sanitized_recommendations.append(clean_rec)
            
            sanitized["recommendations"] = sanitized_recommendations
        
        # Validate confidence score
        if "confidence_score" in sanitized:
            try:
                confidence = float(sanitized["confidence_score"])
                if 0.0 <= confidence <= 1.0:
                    sanitized["confidence_score"] = confidence
                else:
                    logger.warning(f"Confidence score out of range: {confidence}")
                    sanitized["confidence_score"] = None
            except (ValueError, TypeError):
                logger.warning(f"Invalid confidence score: {sanitized['confidence_score']}")
                sanitized["confidence_score"] = None
        
        return sanitized
