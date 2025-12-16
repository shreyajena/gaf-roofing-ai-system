"""AI insights generation engine"""

import json
from typing import Dict, Optional
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models import Contractor, Insight
from app.config import get_settings

settings = get_settings()


class AIInsightsEngine:
    """Engine for generating AI-powered sales insights"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
    
    def generate_insights(self, contractor: Contractor) -> Insight:
        """
        Generate AI insights for a contractor
        
        Args:
            contractor: Contractor object
            
        Returns:
            Insight object
        """
        # Prepare contractor data for AI
        contractor_data = self._prepare_contractor_data(contractor)
        
        # Generate insights using AI
        ai_response = self._call_ai_api(contractor_data)
        
        # Parse and create insight
        insight = self._parse_ai_response(contractor.id, ai_response)
        
        # Save to database
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        
        return insight
    
    def _prepare_contractor_data(self, contractor: Contractor) -> Dict:
        """Prepare contractor data for AI processing"""
        return {
            "name": contractor.name,
            "business_name": contractor.business_name,
            "address": contractor.address,
            "phone": contractor.phone,
            "website": contractor.website,
            "description": contractor.description,
            "services": contractor.services,
            "certifications": contractor.certifications,
            "zipcode": contractor.zipcode,
        }
    
    def _call_ai_api(self, contractor_data: Dict) -> Dict:
        """
        Call AI API to generate insights
        
        Args:
            contractor_data: Contractor information dictionary
            
        Returns:
            AI response dictionary
        """
        if not self.client:
            # Fallback to mock response if API key not configured
            return self._mock_ai_response(contractor_data)
        
        prompt = self._build_prompt(contractor_data)
        
        try:
            response = self.client.chat.completions.create(
                model=settings.ai_model,
                messages=[
                    {"role": "system", "content": "You are a B2B sales intelligence assistant specializing in roofing contractors."},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.ai_temperature,
                max_tokens=settings.max_tokens
            )
            
            content = response.choices[0].message.content
            return json.loads(content) if content else {}
            
        except Exception as e:
            print(f"Error calling AI API: {e}")
            return self._mock_ai_response(contractor_data)
    
    def _build_prompt(self, contractor_data: Dict) -> str:
        """Build prompt for AI API"""
        return f"""
        Analyze the following roofing contractor information and generate actionable sales insights:
        
        Contractor Information:
        - Name: {contractor_data.get('name', 'N/A')}
        - Business Name: {contractor_data.get('business_name', 'N/A')}
        - Location: {contractor_data.get('address', 'N/A')}
        - Zipcode: {contractor_data.get('zipcode', 'N/A')}
        - Website: {contractor_data.get('website', 'N/A')}
        - Description: {contractor_data.get('description', 'N/A')}
        - Services: {contractor_data.get('services', 'N/A')}
        - Certifications: {contractor_data.get('certifications', 'N/A')}
        
        Please provide:
        1. A brief summary of the contractor
        2. Industry type/classification
        3. 3-5 engagement talking points for sales outreach
        4. Potential value assessment (High/Medium/Low)
        
        Return your response as JSON with keys: summary, industry_type, talking_points (array), potential_value
        """
    
    def _parse_ai_response(self, contractor_id: int, ai_response: Dict) -> Insight:
        """Parse AI response into Insight object"""
        talking_points = ai_response.get("talking_points", [])
        if isinstance(talking_points, list):
            talking_points = json.dumps(talking_points)
        
        return Insight(
            contractor_id=contractor_id,
            summary=ai_response.get("summary", ""),
            industry_type=ai_response.get("industry_type", ""),
            engagement_talking_points=talking_points,
            potential_value=ai_response.get("potential_value", "Medium"),
            ai_model_used=settings.ai_model,
            generation_metadata={"temperature": settings.ai_temperature}
        )
    
    def _mock_ai_response(self, contractor_data: Dict) -> Dict:
        """Generate mock AI response for testing"""
        return {
            "summary": f"{contractor_data.get('name', 'Contractor')} is a roofing contractor operating in zipcode {contractor_data.get('zipcode', 'N/A')}.",
            "industry_type": "Residential Roofing Contractor",
            "talking_points": [
                "Discuss GAF product portfolio and certifications",
                "Explore partnership opportunities",
                "Review recent projects and capabilities"
            ],
            "potential_value": "Medium"
        }

