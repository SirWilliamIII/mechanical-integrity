"""Update confidence_level comment to reflect dynamic calculation

Revision ID: 6302519e0189
Revises: 840717ccf284
Create Date: 2025-08-24 22:31:54.967505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6302519e0189'
down_revision: Union[str, None] = '840717ccf284'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update confidence_level comment to reflect it's now calculated dynamically
    op.alter_column('inspection_records', 'confidence_level',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               comment='Statistical confidence in corrosion rate (0-100%) - calculated based on reading count and historical data',
               existing_comment='Statistical confidence in corrosion rate (0-100%)',
               existing_nullable=False)


def downgrade() -> None:
    # Revert comment back to original
    op.alter_column('inspection_records', 'confidence_level',
               existing_type=sa.NUMERIC(precision=5, scale=2),
               comment='Statistical confidence in corrosion rate (0-100%)',
               existing_comment='Statistical confidence in corrosion rate (0-100%) - calculated based on reading count and historical data',
               existing_nullable=False)