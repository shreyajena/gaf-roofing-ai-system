"""FastAPI backend application"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from app.config import get_settings
from app.models import get_db, Contractor, Insight
from app.data_collection import GAFScraper
from app.data_processing import ETLPipeline
from app.ai_insights import AIInsightsEngine

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered B2B sales intelligence platform for roofing contractors",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    from app.models import init_db
    init_db()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GAF Roofing AI System API",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/scrape")
async def scrape_contractors(
    zipcode: str = None,
    distance: int = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Scrape contractors from GAF directory
    
    Args:
        zipcode: ZIP code for search
        distance: Search radius in miles
        background_tasks: FastAPI background tasks
        db: Database session
    """
    scraper = GAFScraper(zipcode=zipcode, distance=distance)
    raw_data = scraper.scrape_contractors()
    
    if not raw_data:
        raise HTTPException(status_code=404, detail="No contractors found")
    
    # Process data through ETL pipeline
    etl = ETLPipeline(db)
    contractors = etl.run(raw_data)
    
    # Generate insights in background
    if background_tasks:
        ai_engine = AIInsightsEngine(db)
        for contractor in contractors:
            background_tasks.add_task(ai_engine.generate_insights, contractor)
    
    return {
        "message": f"Scraped {len(contractors)} contractors",
        "contractors_count": len(contractors)
    }


@app.get("/contractors", response_model=List[dict])
async def get_contractors(
    skip: int = 0,
    limit: int = 100,
    zipcode: str = None,
    db: Session = Depends(get_db)
):
    """
    Get list of contractors
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        zipcode: Filter by zipcode
        db: Database session
    """
    query = db.query(Contractor)
    
    if zipcode:
        query = query.filter(Contractor.zipcode == zipcode)
    
    contractors = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "business_name": c.business_name,
            "zipcode": c.zipcode,
            "phone": c.phone,
            "website": c.website,
            "address": c.address
        }
        for c in contractors
    ]


@app.get("/contractors/{contractor_id}")
async def get_contractor(contractor_id: int, db: Session = Depends(get_db)):
    """Get contractor by ID"""
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    return {
        "id": contractor.id,
        "name": contractor.name,
        "business_name": contractor.business_name,
        "zipcode": contractor.zipcode,
        "address": contractor.address,
        "phone": contractor.phone,
        "email": contractor.email,
        "website": contractor.website,
        "description": contractor.description,
        "services": contractor.services,
        "certifications": contractor.certifications
    }


@app.get("/contractors/{contractor_id}/insights")
async def get_contractor_insights(contractor_id: int, db: Session = Depends(get_db)):
    """Get AI insights for a contractor"""
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    insights = db.query(Insight).filter(Insight.contractor_id == contractor_id).all()
    
    if not insights:
        # Generate insights if none exist
        ai_engine = AIInsightsEngine(db)
        insight = ai_engine.generate_insights(contractor)
        insights = [insight]
    
    return [
        {
            "id": i.id,
            "summary": i.summary,
            "industry_type": i.industry_type,
            "talking_points": i.engagement_talking_points,
            "potential_value": i.potential_value,
            "created_at": i.created_at.isoformat() if i.created_at else None
        }
        for i in insights
    ]


@app.post("/contractors/{contractor_id}/generate-insights")
async def generate_insights(contractor_id: int, db: Session = Depends(get_db)):
    """Generate new AI insights for a contractor"""
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    ai_engine = AIInsightsEngine(db)
    insight = ai_engine.generate_insights(contractor)
    
    return {
        "id": insight.id,
        "summary": insight.summary,
        "industry_type": insight.industry_type,
        "talking_points": insight.engagement_talking_points,
        "potential_value": insight.potential_value
    }

