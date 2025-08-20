"""
API 579 Calculation Engine with Dual-Path Verification

This module implements safety-critical calculations following API 579-1/ASME FFS-1
standards with dual-path verification to ensure 99.99% accuracy.

CRITICAL: All calculations MUST use Decimal type for precision.
         Never use float for any safety-critical calculation.
"""
from decimal import Decimal, getcontext

# Set precision for API 579 calculations (8 significant figures)
getcontext().prec = 8

from .dual_path_calculator import API579Calculator, VerifiedResult, CalculationDiscrepancyError
from .verification import CalculationVerifier
from .constants import API579Constants

__all__ = [
    'API579Calculator',
    'VerifiedResult', 
    'CalculationDiscrepancyError',
    'CalculationVerifier',
    'API579Constants'
]
