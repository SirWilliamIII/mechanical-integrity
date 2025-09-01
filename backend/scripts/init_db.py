# backend/scripts/init_db.py
from models.database import Base, engine

def init_database():
    """Initialize database tables"""
    print("Creating database tables...")
    # TODO: [DATABASE-SCHEMA] Add audit_trail table creation for compliance
    # Compliance audit found missing audit_trail table (ref: compliance_audit_report.md line 36)
    # Error: relation "audit_trail" does not exist in query execution
    # Solution: Run `uv run alembic revision --autogenerate -m "add audit trail table"`
    # Priority: MEDIUM - required for full regulatory audit trail compliance
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

if __name__ == "__main__":
    init_database()
