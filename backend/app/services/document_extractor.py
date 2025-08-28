"""
Document extraction service with EXPLICIT hallucination tracking.
Every extraction includes confidence and source mapping.
"""
import json
import re
from typing import Dict, List, Tuple, Optional
import asyncio
from dataclasses import dataclass
from datetime import datetime
import tempfile
import os

import ollama
from pypdf import PdfReader
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ OCR libraries not available. Install with: uv add pytesseract Pillow pdf2image")


@dataclass
class ExtractionResult:
    """Every extraction must track its source and confidence."""
    value: any
    source_text: str
    page_num: int
    confidence: float
    extraction_method: str  # 'regex', 'llm', 'hybrid'
    warnings: List[str] = None


class InspectionDocumentExtractor:
    """
    Extract structured data from inspection PDFs.
    Key principle: Every value is traceable to source text.
    """
    
    # Common patterns in inspection reports
    PATTERNS = {
        'equipment_tag': [
            r'(?:Equipment|Vessel|Tank|Tag)[\s:#]*([A-Z]-?\d{3,4}[A-Z]?)',
            r'(?:Tag|ID)[\s:#]*([A-Z]{1,3}-?\d{3,4})',
        ],
        'thickness': [
            r'(\d+\.?\d*)\s*(?:inches|in|")',
            r'(\d+\.?\d*)\s*(?:mm|millimeters)',
        ],
        'date': [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
        ],
        'pressure': [
            r'(\d+\.?\d*)\s*(?:psi|PSI|psig|PSIG)',
            r'(\d+\.?\d*)\s*(?:bar|Bar|BAR)',
        ]
    }
    
    def __init__(self, model_name: str = "llama3.2"):
        self.model = model_name
        self.client = ollama.Client()
        
    async def extract_from_pdf(self, pdf_path: str, force_ocr: bool = False) -> Dict:
        """
        Extract structured data from inspection PDF with OCR fallback.
        Returns extraction results with full source tracking.
        
        Args:
            pdf_path: Path to PDF file
            force_ocr: Force OCR even if text extraction works
        """
        # Step 1: Try direct text extraction first
        pdf_text, page_texts = self._extract_pdf_text(pdf_path)
        
        # Step 2: Check if text extraction was successful or if OCR is forced
        needs_ocr = force_ocr or self._is_scanned_pdf(pdf_text, page_texts)
        
        if needs_ocr and OCR_AVAILABLE:
            print("📷 Scanned PDF detected - using OCR extraction")
            ocr_text, ocr_page_texts = await self._extract_with_ocr(pdf_path)
            # Combine or replace text with OCR results
            pdf_text = pdf_text + "\n\n=== OCR EXTRACTED TEXT ===\n" + ocr_text
            page_texts.extend(ocr_page_texts)
        elif needs_ocr and not OCR_AVAILABLE:
            print("⚠️ Scanned PDF detected but OCR not available")
        
        # Step 3: Try regex patterns first (most reliable)
        regex_results = self._extract_with_regex(page_texts)
        
        # Step 4: Use LLM for complex extractions
        llm_results = await self._extract_with_llm(pdf_text, regex_results)
        
        # Step 5: Validate and combine results
        final_results = self._validate_and_merge(regex_results, llm_results)
        
        return {
            "document_path": pdf_path,
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "total_pages": len([p for p in page_texts if "ocr" not in p.get("source", "")]),
            "ocr_pages": len([p for p in page_texts if "ocr" in p.get("source", "")]),
            "extraction_method": "ocr" if needs_ocr else "text",
            "extractions": final_results,
            "quality_metrics": self._calculate_quality_metrics(final_results)
        }
    
    def _extract_pdf_text(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """Extract text from PDF with page tracking."""
        reader = PdfReader(pdf_path)
        full_text = ""
        page_texts = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            full_text += f"\n--- Page {i+1} ---\n{text}"
            page_texts.append({
                "page_num": i + 1,
                "text": text,
                "source": "text_extraction"
            })
            
        return full_text, page_texts
    
    def _is_scanned_pdf(self, pdf_text: str, page_texts: List[Dict]) -> bool:
        """
        Detect if PDF is scanned (images) rather than text-based.
        
        Heuristics:
        1. Very little text extracted
        2. Mostly whitespace/formatting characters
        3. No meaningful words
        """
        if not pdf_text or len(pdf_text.strip()) < 100:
            return True
            
        # Count actual words vs total characters
        words = re.findall(r'\b[a-zA-Z]{3,}\b', pdf_text)
        word_ratio = len(' '.join(words)) / len(pdf_text) if pdf_text else 0
        
        # If less than 10% meaningful text, likely scanned
        if word_ratio < 0.1:
            return True
            
        # Check for common inspection terms
        inspection_terms = ['thickness', 'inspection', 'equipment', 'vessel', 'tank', 'corrosion', 'pressure']
        found_terms = sum(1 for term in inspection_terms if term.lower() in pdf_text.lower())
        
        # If no inspection-related terms found, might be scanned
        return found_terms == 0
    
    async def _extract_with_ocr(self, pdf_path: str) -> Tuple[str, List[Dict]]:
        """
        Extract text from scanned PDF using OCR.
        
        Returns:
            Tuple of (full_ocr_text, page_texts)
        """
        if not OCR_AVAILABLE:
            return "", []
            
        try:
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=300)  # High DPI for better OCR
            
            full_ocr_text = ""
            page_texts = []
            
            for i, image in enumerate(images):
                # Apply image preprocessing for better OCR
                processed_image = self._preprocess_image_for_ocr(image)
                
                # Extract text using Tesseract with industrial-specific config
                custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,()[]{}:;-/\\ '
                
                try:
                    ocr_text = pytesseract.image_to_string(processed_image, config=custom_config)
                    confidence = self._get_ocr_confidence(processed_image)
                    
                    full_ocr_text += f"\n--- OCR Page {i+1} (Confidence: {confidence:.2f}) ---\n{ocr_text}"
                    page_texts.append({
                        "page_num": i + 1,
                        "text": ocr_text,
                        "source": "ocr",
                        "ocr_confidence": confidence
                    })
                    
                except Exception as e:
                    print(f"OCR failed for page {i+1}: {e}")
                    page_texts.append({
                        "page_num": i + 1,
                        "text": "",
                        "source": "ocr_failed",
                        "error": str(e)
                    })
            
            return full_ocr_text, page_texts
            
        except Exception as e:
            print(f"OCR extraction failed: {e}")
            return "", []
    
    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.
        
        Common preprocessing for industrial documents:
        1. Convert to grayscale
        2. Increase contrast
        3. Remove noise
        """
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # You could add more sophisticated preprocessing here:
            # - Deskewing
            # - Noise removal
            # - Contrast enhancement
            # - Edge sharpening
            
            return image
        except Exception as e:
            print(f"Image preprocessing failed: {e}")
            return image
    
    def _get_ocr_confidence(self, image: Image.Image) -> float:
        """
        Get OCR confidence score for the extracted text.
        """
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            return sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
        except:
            return 0.5  # Default medium confidence
    
    def _extract_with_regex(self, page_texts: List[Dict]) -> Dict[str, List[ExtractionResult]]:
        """Extract using deterministic regex patterns."""
        results = {key: [] for key in self.PATTERNS.keys()}
        
        for page in page_texts:
            text = page["text"]
            page_num = page["page_num"]
            
            # Try each pattern type
            for field, patterns in self.PATTERNS.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        # Extract surrounding context
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end].strip()
                        
                        results[field].append(ExtractionResult(
                            value=match.group(1),
                            source_text=context,
                            page_num=page_num,
                            confidence=0.95,  # High confidence for regex
                            extraction_method="regex"
                        ))
        
        return results
    
    async def _extract_with_llm(self, full_text: str, regex_results: Dict) -> Dict[str, List[ExtractionResult]]:
        """Use LLM for complex extractions with explicit instructions."""
        
        # Build context from regex results
        found_context = self._build_context_from_regex(regex_results)
        
        prompt = f"""You are extracting data from an inspection report. 
        
Already found via pattern matching:
{found_context}

CRITICAL RULES:
1. Only extract values that EXACTLY appear in the text
2. Always include the exact source text where you found each value
3. If you calculate or infer anything, mark it with WARNING
4. Use confidence scores: 1.0 = exact match, <0.8 = inference

Extract the following if present in the text:
- Equipment details (type, material, size)
- Inspection findings (corrosion, pitting, recommendations)  
- Thickness measurements not already found
- Inspector name and credentials
- Next inspection recommendations

Text to analyze:
{full_text[:3000]}  # Limit context size

Respond in JSON format:
{{
    "extractions": [
        {{
            "field": "field_name",
            "value": "extracted_value",
            "source_quote": "exact text where found",
            "confidence": 0.95,
            "warning": null or "reason for warning"
        }}
    ]
}}"""

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                options={"temperature": 0.1}  # Low temp for consistency
            )
            
            llm_data = json.loads(response['response'])
            return self._parse_llm_response(llm_data, full_text)
            
        except Exception as e:
            print(f"LLM extraction error: {e}")
            return {}
    
    def _validate_and_merge(self, regex_results: Dict, llm_results: Dict) -> Dict:
        """Merge results with validation and deduplication."""
        final_results = {}
        
        # Start with high-confidence regex results
        for field, extractions in regex_results.items():
            if extractions:
                # Remove duplicates, keep highest confidence
                unique_values = {}
                for ext in extractions:
                    key = str(ext.value).lower().strip()
                    if key not in unique_values or ext.confidence > unique_values[key].confidence:
                        unique_values[key] = ext
                
                final_results[field] = list(unique_values.values())
        
        # Add LLM results that don't conflict
        for field, extractions in llm_results.items():
            if field not in final_results:
                final_results[field] = extractions
            else:
                # Check for conflicts
                existing_values = {str(e.value).lower().strip() for e in final_results[field]}
                for ext in extractions:
                    if str(ext.value).lower().strip() not in existing_values:
                        # Flag potential hallucination if no source
                        if not ext.source_text or ext.confidence < 0.8:
                            if not ext.warnings:
                                ext.warnings = []
                            ext.warnings.append("Low confidence - requires verification")
                        final_results[field].append(ext)
        
        return final_results
    
    def _calculate_quality_metrics(self, results: Dict) -> Dict:
        """Calculate extraction quality metrics."""
        total_extractions = sum(len(exts) for exts in results.values())
        high_confidence = sum(
            1 for exts in results.values() 
            for ext in exts if ext.confidence >= 0.9
        )
        with_warnings = sum(
            1 for exts in results.values() 
            for ext in exts if ext.warnings
        )
        
        return {
            "total_extractions": total_extractions,
            "high_confidence_ratio": high_confidence / max(total_extractions, 1),
            "extractions_with_warnings": with_warnings,
            "fields_extracted": len(results)
        }
    
    def _build_context_from_regex(self, regex_results: Dict) -> str:
        """Build context string from regex results."""
        context_parts = []
        for field, extractions in regex_results.items():
            if extractions:
                values = [str(ext.value) for ext in extractions[:3]]  # First 3
                context_parts.append(f"{field}: {', '.join(values)}")
        return "\n".join(context_parts)
    
    def _parse_llm_response(self, llm_data: Dict, full_text: str) -> Dict[str, List[ExtractionResult]]:
        """Parse LLM response into ExtractionResult objects."""
        results = {}
        
        for extraction in llm_data.get("extractions", []):
            field = extraction.get("field", "unknown")
            
            # Verify the source quote actually exists in the text
            source_quote = extraction.get("source_quote", "")
            if source_quote and source_quote in full_text:
                # Find page number
                page_num = self._find_page_number(source_quote, full_text)
                
                if field not in results:
                    results[field] = []
                
                results[field].append(ExtractionResult(
                    value=extraction.get("value"),
                    source_text=source_quote,
                    page_num=page_num,
                    confidence=extraction.get("confidence", 0.5),
                    extraction_method="llm",
                    warnings=[extraction.get("warning")] if extraction.get("warning") else None
                ))
            else:
                # Potential hallucination - source not found
                print(f"WARNING: LLM claimed to find '{extraction.get('value')}' but source not in text")
        
        return results
    
    def _find_page_number(self, text_snippet: str, full_text: str) -> int:
        """Find which page contains the text snippet."""
        # Simple approach - could be improved
        pages = full_text.split("--- Page ")
        for i, page_text in enumerate(pages[1:], 1):
            if text_snippet in page_text:
                return i
        return 0  # Unknown page


# Quick test function
async def test_extractor():
    """Test the extractor with a sample PDF."""
    InspectionDocumentExtractor()
    
    # You'll need to provide a real PDF path
    # results = await extractor.extract_from_pdf("/path/to/inspection.pdf")
    # print(json.dumps(results, indent=2, default=str))
    
    print("Extractor ready. Key features:")
    print("- Every extraction traceable to source")
    print("- Confidence scores on everything")  
    print("- Warnings for potential hallucinations")
    print("- Regex first, LLM for complex stuff")


if __name__ == "__main__":
    asyncio.run(test_extractor())
