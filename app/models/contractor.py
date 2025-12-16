"""Contractor data model for GAF scraping"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.database import Base


class Contractor(Base):
    """Main contractor table with structured data"""
    
    __tablename__ = "contractors"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Listing-level data (from search results)
    contractor_name = Column(String(255), nullable=False, index=True)
    rating = Column(Float)  # e.g., 4.5
    review_count = Column(Integer, default=0)
    city = Column(String(100))
    state = Column(String(50))
    profile_url = Column(String(1000))
    external_contractor_id = Column(String(100), unique=True, index=True)  # Derived from URL
    
    # Profile-level structured data
    years_in_business = Column(Integer)  # Normalized
    business_start_year = Column(Integer)
    employee_range = Column(String(50))  # e.g., "1-10", "11-50"
    state_license_number = Column(String(100))
    address = Column(Text)
    phone = Column(String(50))
    
    # Metadata
    data_confidence = Column(String(20), default="medium")  # high / medium / low
    last_scraped_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    certifications = relationship("Certification", back_populates="contractor", cascade="all, delete-orphan")
    text_data = relationship("ContractorText", back_populates="contractor", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Contractor(name='{self.contractor_name}', city='{self.city}', state='{self.state}')>"


class Certification(Base):
    """Contractor certifications (many-to-one relationship)"""
    
    __tablename__ = "certifications"
    
    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False, index=True)
    
    # Certification data
    name = Column(String(255), nullable=False)  # Normalized certification name
    original_text = Column(String(500))  # Original badge text/alt text from scraping
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    contractor = relationship("Contractor", back_populates="certifications")
    
    def __repr__(self):
        return f"<Certification(name='{self.name}', contractor_id={self.contractor_id})>"


class ContractorText(Base):
    """Unstructured text data for contractors"""
    
    __tablename__ = "contractor_text"
    
    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False, unique=True, index=True)
    
    # Unstructured text fields
    about_text = Column(Text)  # Full about section text
    review_snippets = Column(Text)  # Concatenated top 3-5 reviews
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    contractor = relationship("Contractor", back_populates="text_data")
    
    def __repr__(self):
        return f"<ContractorText(contractor_id={self.contractor_id})>"
