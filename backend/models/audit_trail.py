"""
Immutable Audit Trail System for API 579 Compliance.
Provides cryptographic integrity verification and regulatory compliance.
"""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
from sqlalchemy import String, Text, DateTime, Boolean, DECIMAL, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from models.base import BaseModel, GUID


class AuditEventType(str, Enum):
    """Types of audit events tracked for regulatory compliance."""
    CALCULATION_CREATED = "calculation_created"
    CALCULATION_VERIFIED = "calculation_verified"
    INSPECTION_CREATED = "inspection_created"
    INSPECTION_VERIFIED = "inspection_verified"
    EQUIPMENT_MODIFIED = "equipment_modified"
    DIMENSION_UPDATED = "dimension_updated"
    MATERIAL_CHANGED = "material_changed"
    SYSTEM_ACCESS = "system_access"


class AuditTrail(BaseModel):
    """
    Immutable audit trail record for regulatory compliance.
    
    Records cannot be modified after creation to ensure
    regulatory integrity per API 510/570/653 requirements.
    """
    __tablename__ = "audit_trail"
    
    # Primary audit information
    event_type: Mapped[AuditEventType] = mapped_column(
        comment="Type of event being audited"
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        comment="Type of entity (equipment, inspection, calculation)"
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        comment="UUID of the entity being audited"
    )
    
    # Event details
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        comment="Exact timestamp of the event"
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User who performed the action"
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Session identifier for traceability"
    )
    
    # Data integrity
    before_state: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON snapshot of entity state before change"
    )
    after_state: Mapped[str] = mapped_column(
        Text,
        comment="JSON snapshot of entity state after change"
    )
    changes_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable summary of changes"
    )
    
    # Regulatory compliance
    regulatory_significance: Mapped[bool] = mapped_column(
        default=True,
        comment="Whether this event has regulatory significance"
    )
    api_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="API 579/510/570/653 clause reference if applicable"
    )
    
    # Cryptographic integrity
    content_hash: Mapped[str] = mapped_column(
        String(64),
        comment="SHA-256 hash of audit content for integrity verification"
    )
    chain_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Hash linking to previous audit record (blockchain-style)"
    )
    
    # Additional metadata
    system_version: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="System version when event occurred"
    )
    calculation_method: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Calculation method used if applicable"
    )
    
    # Immutability enforcement
    immutable: Mapped[bool] = mapped_column(
        default=True,
        comment="Flag indicating record is immutable"
    )


class AuditTrailManager:
    """
    Manager for creating and verifying immutable audit trails.
    
    Ensures regulatory compliance and data integrity for
    safety-critical calculations and inspections.
    """
    
    @staticmethod
    def create_audit_record(
        session,
        event_type: AuditEventType,
        entity_type: str,
        entity_id: str,
        after_state: Dict[str, Any],
        before_state: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        changes_summary: Optional[str] = None,
        api_reference: Optional[str] = None,
        system_version: Optional[str] = None,
        calculation_method: Optional[str] = None
    ) -> AuditTrail:
        """
        Create an immutable audit trail record.
        
        Args:
            session: Database session
            event_type: Type of audit event
            entity_type: Type of entity being audited
            entity_id: UUID of entity
            after_state: Complete state after change
            before_state: State before change (if applicable)
            user_id: User performing action
            session_id: Session identifier
            changes_summary: Human-readable change description
            api_reference: Relevant API standard clause
            system_version: Software version
            calculation_method: Calculation method used
            
        Returns:
            Created audit trail record
        """
        # Serialize states to JSON with consistent formatting
        after_json = json.dumps(after_state, sort_keys=True, default=str, indent=None)
        before_json = None
        if before_state:
            before_json = json.dumps(before_state, sort_keys=True, default=str, indent=None)
        
        # Get previous audit record for chain hashing
        previous_audit = session.query(AuditTrail).filter(
            AuditTrail.entity_id == entity_id,
            AuditTrail.entity_type == entity_type
        ).order_by(AuditTrail.created_at.desc()).first()
        
        chain_hash = None
        if previous_audit:
            chain_hash = previous_audit.content_hash
        
        # Create audit record
        audit_record = AuditTrail(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            event_timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            before_state=before_json,
            after_state=after_json,
            changes_summary=changes_summary,
            api_reference=api_reference,
            chain_hash=chain_hash,
            system_version=system_version,
            calculation_method=calculation_method
        )
        
        # Calculate content hash for integrity verification
        audit_record.content_hash = AuditTrailManager._calculate_content_hash(audit_record)
        
        return audit_record
    
    @staticmethod
    def _calculate_content_hash(audit_record: AuditTrail) -> str:
        """
        Calculate SHA-256 hash of audit record content for integrity verification.
        
        Args:
            audit_record: Audit record to hash
            
        Returns:
            SHA-256 hash as hexadecimal string
        """
        # Create hash content from immutable fields
        hash_content = {
            'event_type': audit_record.event_type.value,
            'entity_type': audit_record.entity_type,
            'entity_id': audit_record.entity_id,
            'event_timestamp': audit_record.event_timestamp.isoformat(),
            'before_state': audit_record.before_state,
            'after_state': audit_record.after_state,
            'chain_hash': audit_record.chain_hash,
            'user_id': audit_record.user_id,
            'system_version': audit_record.system_version
        }
        
        # Create consistent JSON representation
        hash_json = json.dumps(hash_content, sort_keys=True, default=str)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(hash_json.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_audit_integrity(session, audit_record: AuditTrail) -> Dict[str, Any]:
        """
        Verify cryptographic integrity of audit trail record.
        
        Args:
            session: Database session
            audit_record: Audit record to verify
            
        Returns:
            Dictionary with verification results
        """
        verification_result = {
            'valid': False,
            'hash_valid': False,
            'chain_valid': False,
            'timestamp_valid': False,
            'errors': []
        }
        
        # Verify content hash
        expected_hash = AuditTrailManager._calculate_content_hash(audit_record)
        if expected_hash == audit_record.content_hash:
            verification_result['hash_valid'] = True
        else:
            verification_result['errors'].append(
                f"Content hash mismatch: expected {expected_hash}, got {audit_record.content_hash}"
            )
        
        # Verify chain integrity
        if audit_record.chain_hash:
            previous_audit = session.query(AuditTrail).filter(
                AuditTrail.entity_id == audit_record.entity_id,
                AuditTrail.entity_type == audit_record.entity_type,
                AuditTrail.created_at < audit_record.created_at
            ).order_by(AuditTrail.created_at.desc()).first()
            
            if previous_audit and previous_audit.content_hash == audit_record.chain_hash:
                verification_result['chain_valid'] = True
            else:
                verification_result['errors'].append("Chain hash does not match previous record")
        else:
            # First record in chain
            verification_result['chain_valid'] = True
        
        # Verify timestamp is reasonable
        if audit_record.event_timestamp <= datetime.utcnow():
            verification_result['timestamp_valid'] = True
        else:
            verification_result['errors'].append("Event timestamp is in the future")
        
        # Overall validity
        verification_result['valid'] = (
            verification_result['hash_valid'] and
            verification_result['chain_valid'] and
            verification_result['timestamp_valid']
        )
        
        return verification_result
    
    @staticmethod
    def get_entity_audit_trail(
        session,
        entity_type: str,
        entity_id: str,
        limit: Optional[int] = None
    ) -> List[AuditTrail]:
        """
        Get complete audit trail for an entity.
        
        Args:
            session: Database session
            entity_type: Type of entity
            entity_id: Entity UUID
            limit: Maximum number of records to return
            
        Returns:
            List of audit trail records in chronological order
        """
        query = session.query(AuditTrail).filter(
            AuditTrail.entity_type == entity_type,
            AuditTrail.entity_id == entity_id
        ).order_by(AuditTrail.event_timestamp.asc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()


# Database event listeners to prevent modification of audit records
@event.listens_for(AuditTrail, 'before_update')
def prevent_audit_modification(mapper, connection, target):
    """Prevent modification of immutable audit records."""
    if target.immutable:
        raise SQLAlchemyError(
            f"Audit trail record {target.id} is immutable and cannot be modified. "
            f"This violates regulatory compliance requirements."
        )


@event.listens_for(AuditTrail, 'before_delete')
def prevent_audit_deletion(mapper, connection, target):
    """Prevent deletion of audit records."""
    raise SQLAlchemyError(
        f"Audit trail record {target.id} cannot be deleted. "
        f"This violates regulatory compliance requirements."
    )