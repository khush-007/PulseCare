from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from backend.app.core.database import Base


class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, index=True, nullable=False)
    generic_name = Column(String(150), index=True, nullable=False)
    dosage_form = Column(String(100), nullable=False)  # Tablet, Capsule, Syrup, Injection, etc.
    standard_dosage = Column(String(255), nullable=False)
    indications = Column(Text, nullable=False)          # What it treats
    contraindications = Column(Text, nullable=False)    # When not to use
    side_effects = Column(Text, nullable=False)         # Common side effects
    requires_prescription = Column(Boolean, default=True, nullable=False)
    price = Column(Float, default=15.0, nullable=False)
