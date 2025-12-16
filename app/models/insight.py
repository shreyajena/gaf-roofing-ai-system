"""AI-generated insights model"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.database import Base


class Insight(Base):
    """AI-generated insights for contractors"""
    
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False, index=True)
    
    # Insight Content
    summary = Column(Text)
    industry_type = Column(String(255))
    engagement_talking_points = Column(Text)  # JSON string or text
    potential_value = Column(String(50))  # e.g., "High", "Medium", "Low"
    
    # AI Metadata
    ai_model_used = Column(String(100))
    generation_metadata = Column(JSON)  # Store additional metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    contractor = relationship("Contractor", backref="insights")
    
    def __repr__(self):
        return f"<Insight(contractor_id={self.contractor_id}, industry_type='{self.industry_type}')>"

