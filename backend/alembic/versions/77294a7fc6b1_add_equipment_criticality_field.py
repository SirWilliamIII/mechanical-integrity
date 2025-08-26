"""add equipment criticality field

Revision ID: 77294a7fc6b1
Revises: 6302519e0189
Create Date: 2025-08-25 16:34:21.660756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '77294a7fc6b1'
down_revision: Union[str, None] = '6302519e0189'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type first
    equipment_criticality_enum = sa.Enum('HIGH', 'MEDIUM', 'LOW', name='equipmentcriticality')
    equipment_criticality_enum.create(op.get_bind())
    
    # Add criticality column to equipment table  
    op.add_column('equipment', sa.Column('criticality', equipment_criticality_enum, server_default='MEDIUM', nullable=False, comment='Equipment criticality level for risk-based inspection'))


def downgrade() -> None:
    # Remove criticality column and enum
    op.drop_column('equipment', 'criticality')
    op.execute('DROP TYPE IF EXISTS equipmentcriticality')