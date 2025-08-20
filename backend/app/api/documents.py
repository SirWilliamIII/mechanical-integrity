"""
API endpoints for document processing.
Real extraction, real confidence tracking.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
import tempfile
import os
from pathlib import Path

from app.services.document_extractor import InspectionDocumentExtractor


router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Initialize extractor
extractor = InspectionDocumentExtractor()


@router.post("/extract")
async def extract_inspection_data(file: UploadFile = File(...)):
    """
    Extract structured data from inspection PDF.
    
    Returns:
    - Extracted data with confidence scores
    - Source references for every value
    - Warnings for low-confidence extractions
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files supported")
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Extract data
        results = await extractor.extract_from_pdf(tmp_path)
        
        # Check quality metrics
        metrics = results.get("quality_metrics", {})
        if metrics.get("high_confidence_ratio", 0) < 0.5:
            results["warning"] = "Low confidence extraction - manual review recommended"
        
        # Format response
        response = {
            "status": "success",
            "filename": file.filename,
            "extractions": _format_extractions(results["extractions"]),
            "metrics": metrics,
            "requires_review": metrics.get("extractions_with_warnings", 0) > 0
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(500, f"Extraction failed: {str(e)}")
        
    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/extraction-demo")
async def get_demo_data():
    """
    Show what a successful extraction looks like.
    This is what we're building towards.
    """
    return {
        "demo_extraction": {
            "equipment_tag": {
                "value": "V-101",
                "confidence": 0.95,
                "source": "Equipment Tag: V-101",
                "page": 1,
                "method": "regex"
            },
            "thickness_measurements": [
                {
                    "value": 0.425,
                    "confidence": 0.98,
                    "source": "Minimum thickness recorded: 0.425 inches",
                    "page": 3,
                    "method": "regex"
                },
                {
                    "value": 0.387,
                    "confidence": 0.75,
                    "source": "inspector noted 'approximately 0.387' near weld",
                    "page": 4,
                    "method": "llm",
                    "warning": "Approximate value - verify"
                }
            ],
            "next_inspection": {
                "value": "2025-03-15",
                "confidence": 0.85,
                "source": "Recommend re-inspection by March 2025",
                "page": 8,
                "method": "llm"
            },
            "corrosion_rate": {
                "value": null,
                "confidence": 0,
                "note": "Not found in document - would need calculation"
            }
        },
        "quality_summary": {
            "total_extractions": 15,
            "high_confidence": 12,
            "requiring_verification": 3,
            "hallucination_risk": "Low - all values traced to source"
        }
    }


def _format_extractions(extractions: Dict) -> Dict:
    """Format extraction results for API response."""
    formatted = {}
    
    for field, extraction_list in extractions.items():
        if not extraction_list:
            continue
            
        # Take highest confidence extraction for each field
        best = max(extraction_list, key=lambda x: x.confidence)
        
        formatted[field] = {
            "value": best.value,
            "confidence": best.confidence,
            "source": best.source_text[:100] + "..." if len(best.source_text) > 100 else best.source_text,
            "page": best.page_num,
            "method": best.extraction_method,
            "alternatives": len(extraction_list) - 1,
            "warnings": best.warnings
        }
        
        # Include alternatives if multiple found
        if len(extraction_list) > 1:
            formatted[field]["all_values"] = [
                {
                    "value": ext.value,
                    "confidence": ext.confidence,
                    "page": ext.page_num
                }
                for ext in extraction_list
            ]
    
    return formatted
