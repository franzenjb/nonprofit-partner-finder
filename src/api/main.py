from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import json
import io
import csv

from src.core.ranking_engine import NonprofitRankingEngine, RankingCriteria
from src.collectors.irs_collector import IRS990Collector
from src.collectors.web_scraper import NonprofitWebScraper
from src.collectors.social_media import SocialMediaCollector
from src.models.nonprofit import Nonprofit


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Red Cross Nonprofit Partner Finder",
    description="AI-powered system for identifying and ranking nonprofit partners aligned with Red Cross mission",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
irs_collector = IRS990Collector()
web_scraper = NonprofitWebScraper()
social_collector = SocialMediaCollector()
ranking_engine = NonprofitRankingEngine()


# Pydantic models for API
class NonprofitSearchRequest(BaseModel):
    zip_code: str = Field(..., description="ZIP code to search")
    radius_miles: int = Field(25, description="Search radius in miles")
    min_revenue: Optional[float] = Field(None, description="Minimum annual revenue")
    max_results: int = Field(20, description="Maximum number of results")
    
class NonprofitResponse(BaseModel):
    ein: str
    name: str
    rank: int
    overall_score: float
    mission_alignment_score: Optional[float]
    roi_potential: Optional[float]
    website: Optional[str]
    mission_statement: Optional[str]
    explanation: str
    
class DetailedNonprofitResponse(BaseModel):
    ein: str
    name: str
    rank: int
    overall_score: float
    mission_alignment: Optional[Dict[str, Any]]
    partnership_roi: Optional[Dict[str, Any]]
    financial_summary: Optional[Dict[str, Any]]
    programs: List[str]
    social_media: Optional[List[Dict[str, Any]]]
    explanation: str

class RankingCustomization(BaseModel):
    mission_weight: float = Field(0.35, ge=0, le=1)
    roi_weight: float = Field(0.25, ge=0, le=1)
    stability_weight: float = Field(0.15, ge=0, le=1)
    capacity_weight: float = Field(0.15, ge=0, le=1)
    data_quality_weight: float = Field(0.10, ge=0, le=1)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Red Cross Nonprofit Partner Finder API",
        "version": "1.0.0",
        "endpoints": {
            "/search": "Search nonprofits by ZIP code",
            "/nonprofit/{ein}": "Get detailed nonprofit information",
            "/analyze/{ein}": "Perform deep analysis of a nonprofit",
            "/rank": "Rank a list of nonprofits",
            "/compare": "Compare two nonprofits",
            "/export": "Export search results",
            "/docs": "API documentation"
        }
    }


@app.post("/search", response_model=List[NonprofitResponse])
async def search_nonprofits(
    request: NonprofitSearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Search for nonprofits in a ZIP code area and rank by Red Cross alignment
    """
    try:
        logger.info(f"Searching nonprofits in ZIP {request.zip_code}")
        
        # Search for nonprofits using IRS data
        search_results = irs_collector.search_by_zip(
            request.zip_code, 
            request.radius_miles
        )
        
        if not search_results:
            raise HTTPException(status_code=404, detail="No nonprofits found in this area")
        
        # Collect detailed data for each nonprofit
        nonprofits = []
        for result in search_results[:request.max_results]:
            nonprofit = irs_collector.get_nonprofit_details(result['ein'])
            if nonprofit:
                # Skip if below minimum revenue threshold
                if request.min_revenue:
                    latest_financials = nonprofit.get_latest_financials()
                    if latest_financials and latest_financials.total_revenue < request.min_revenue:
                        continue
                
                nonprofits.append(nonprofit)
        
        # Rank nonprofits
        ranked_nonprofits = ranking_engine.rank_nonprofits(nonprofits)
        
        # Background task to collect additional data
        background_tasks.add_task(enrich_nonprofit_data, ranked_nonprofits)
        
        # Format response
        response = []
        for np in ranked_nonprofits:
            response.append(NonprofitResponse(
                ein=np.ein,
                name=np.name,
                rank=np.ranking,
                overall_score=np.overall_score,
                mission_alignment_score=np.mission_alignment.score if np.mission_alignment else None,
                roi_potential=np.partnership_roi.estimated_value if np.partnership_roi else None,
                website=np.website,
                mission_statement=np.mission_statement[:200] + "..." if np.mission_statement and len(np.mission_statement) > 200 else np.mission_statement,
                explanation=ranking_engine.explain_ranking(np)
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/nonprofit/{ein}", response_model=DetailedNonprofitResponse)
async def get_nonprofit_details(ein: str):
    """
    Get detailed information about a specific nonprofit
    """
    try:
        # Get nonprofit data
        nonprofit = irs_collector.get_nonprofit_details(ein)
        if not nonprofit:
            raise HTTPException(status_code=404, detail="Nonprofit not found")
        
        # Perform analysis
        nonprofit.mission_alignment = ranking_engine.mission_analyzer.analyze_alignment(nonprofit)
        nonprofit.partnership_roi = ranking_engine.roi_calculator.calculate_roi(nonprofit)
        nonprofit.overall_score = ranking_engine._calculate_overall_score(nonprofit)
        nonprofit.ranking = 1  # Single nonprofit
        
        # Format financial summary
        financial_summary = None
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials:
            financial_summary = {
                "year": latest_financials.year,
                "total_revenue": latest_financials.total_revenue,
                "total_expenses": latest_financials.total_expenses,
                "program_expense_ratio": latest_financials.program_expense_ratio,
                "overhead_ratio": latest_financials.overhead_ratio
            }
        
        # Format response
        return DetailedNonprofitResponse(
            ein=nonprofit.ein,
            name=nonprofit.name,
            rank=nonprofit.ranking,
            overall_score=nonprofit.overall_score,
            mission_alignment={
                "score": nonprofit.mission_alignment.score,
                "matched_keywords": nonprofit.mission_alignment.matched_keywords,
                "service_overlap": nonprofit.mission_alignment.service_overlap,
                "explanation": nonprofit.mission_alignment.explanation,
                "confidence": nonprofit.mission_alignment.confidence
            } if nonprofit.mission_alignment else None,
            partnership_roi={
                "estimated_value": nonprofit.partnership_roi.estimated_value,
                "cost_savings": nonprofit.partnership_roi.cost_savings,
                "impact_multiplier": nonprofit.partnership_roi.impact_multiplier,
                "reach_expansion": nonprofit.partnership_roi.reach_expansion,
                "explanation": nonprofit.partnership_roi.explanation
            } if nonprofit.partnership_roi else None,
            financial_summary=financial_summary,
            programs=nonprofit.programs,
            social_media=[{
                "platform": sm.platform,
                "followers": sm.followers,
                "engagement_rate": sm.engagement_rate
            } for sm in nonprofit.social_media] if nonprofit.social_media else None,
            explanation=ranking_engine.explain_ranking(nonprofit)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting nonprofit details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/{ein}")
async def analyze_nonprofit(ein: str, background_tasks: BackgroundTasks):
    """
    Perform deep analysis including web scraping and social media
    """
    try:
        # Get basic nonprofit data
        nonprofit = irs_collector.get_nonprofit_details(ein)
        if not nonprofit:
            raise HTTPException(status_code=404, detail="Nonprofit not found")
        
        # Start background analysis tasks
        background_tasks.add_task(deep_analyze_nonprofit, nonprofit)
        
        return {
            "status": "analysis_started",
            "ein": ein,
            "message": "Deep analysis initiated. Results will be available shortly.",
            "check_url": f"/nonprofit/{ein}"
        }
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rank")
async def rank_nonprofits(
    eins: List[str] = Query(..., description="List of EINs to rank"),
    criteria: Optional[RankingCustomization] = None
):
    """
    Rank a custom list of nonprofits
    """
    try:
        # Update ranking criteria if provided
        if criteria:
            ranking_engine.criteria = RankingCriteria(
                mission_weight=criteria.mission_weight,
                roi_weight=criteria.roi_weight,
                stability_weight=criteria.stability_weight,
                capacity_weight=criteria.capacity_weight,
                data_quality_weight=criteria.data_quality_weight
            )
        
        # Collect nonprofit data
        nonprofits = []
        for ein in eins:
            nonprofit = irs_collector.get_nonprofit_details(ein)
            if nonprofit:
                nonprofits.append(nonprofit)
        
        if not nonprofits:
            raise HTTPException(status_code=404, detail="No valid nonprofits found")
        
        # Rank nonprofits
        ranked_nonprofits = ranking_engine.rank_nonprofits(nonprofits)
        
        # Format response
        response = []
        for np in ranked_nonprofits:
            response.append({
                "ein": np.ein,
                "name": np.name,
                "rank": np.ranking,
                "overall_score": np.overall_score,
                "mission_alignment": np.mission_alignment.score if np.mission_alignment else None,
                "roi_potential": np.partnership_roi.estimated_value if np.partnership_roi else None
            })
        
        return response
        
    except Exception as e:
        logger.error(f"Ranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/compare")
async def compare_nonprofits(ein1: str, ein2: str):
    """
    Compare two nonprofits side by side
    """
    try:
        # Get both nonprofits
        nonprofit1 = irs_collector.get_nonprofit_details(ein1)
        nonprofit2 = irs_collector.get_nonprofit_details(ein2)
        
        if not nonprofit1 or not nonprofit2:
            raise HTTPException(status_code=404, detail="One or both nonprofits not found")
        
        # Analyze both
        nonprofits = ranking_engine.rank_nonprofits([nonprofit1, nonprofit2])
        
        # Generate comparison
        comparison = ranking_engine.compare_nonprofits(nonprofits[0], nonprofits[1])
        
        return comparison
        
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/export")
async def export_results(
    zip_code: str,
    format: str = Query("csv", regex="^(csv|json)$")
):
    """
    Export search results in CSV or JSON format
    """
    try:
        # Search and rank nonprofits
        search_results = irs_collector.search_by_zip(zip_code, 25)
        nonprofits = []
        
        for result in search_results[:50]:  # Limit to 50 for export
            nonprofit = irs_collector.get_nonprofit_details(result['ein'])
            if nonprofit:
                nonprofits.append(nonprofit)
        
        ranked_nonprofits = ranking_engine.rank_nonprofits(nonprofits)
        
        if format == "csv":
            # Generate CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "Rank", "EIN", "Name", "Overall Score", "Mission Alignment",
                "ROI Potential", "Annual Revenue", "Program Efficiency",
                "Website", "Mission Statement"
            ])
            
            # Data rows
            for np in ranked_nonprofits:
                latest_financials = np.get_latest_financials()
                writer.writerow([
                    np.ranking,
                    np.ein,
                    np.name,
                    f"{np.overall_score:.2f}",
                    f"{np.mission_alignment.score:.2f}" if np.mission_alignment else "",
                    f"{np.partnership_roi.estimated_value:.0f}" if np.partnership_roi else "",
                    f"{latest_financials.total_revenue:.0f}" if latest_financials else "",
                    f"{latest_financials.program_expense_ratio:.2f}" if latest_financials else "",
                    np.website or "",
                    np.mission_statement[:200] if np.mission_statement else ""
                ])
            
            output.seek(0)
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=nonprofits_{zip_code}.csv"}
            )
        
        else:  # JSON format
            data = []
            for np in ranked_nonprofits:
                latest_financials = np.get_latest_financials()
                data.append({
                    "rank": np.ranking,
                    "ein": np.ein,
                    "name": np.name,
                    "overall_score": np.overall_score,
                    "mission_alignment": {
                        "score": np.mission_alignment.score if np.mission_alignment else None,
                        "explanation": np.mission_alignment.explanation if np.mission_alignment else None
                    },
                    "roi_potential": {
                        "value": np.partnership_roi.estimated_value if np.partnership_roi else None,
                        "explanation": np.partnership_roi.explanation if np.partnership_roi else None
                    },
                    "financials": {
                        "revenue": latest_financials.total_revenue if latest_financials else None,
                        "efficiency": latest_financials.program_expense_ratio if latest_financials else None
                    },
                    "website": np.website,
                    "mission": np.mission_statement
                })
            
            return JSONResponse(content=data)
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background tasks
async def enrich_nonprofit_data(nonprofits: List[Nonprofit]):
    """Background task to enrich nonprofit data with web and social media info"""
    for nonprofit in nonprofits:
        try:
            # Scrape website if available
            if nonprofit.website:
                web_scraper.scrape_nonprofit_website(nonprofit)
            
            # Get social media data
            social_accounts = social_collector.search_social_accounts(nonprofit.name)
            if social_accounts:
                nonprofit.social_media = social_collector.analyze_social_presence(
                    nonprofit.name, social_accounts
                )
            
            # Update data quality score
            nonprofit.data_quality_score = calculate_data_quality(nonprofit)
            
        except Exception as e:
            logger.error(f"Error enriching data for {nonprofit.name}: {e}")


async def deep_analyze_nonprofit(nonprofit: Nonprofit):
    """Perform deep analysis of a single nonprofit"""
    try:
        # Web scraping
        if nonprofit.website:
            web_data = web_scraper.scrape_nonprofit_website(nonprofit)
            logger.info(f"Scraped website for {nonprofit.name}")
        
        # Social media analysis
        social_accounts = social_collector.search_social_accounts(nonprofit.name)
        if not social_accounts and nonprofit.website:
            # Try to find social links from website
            pass  # Would extract from web_data
        
        if social_accounts:
            nonprofit.social_media = social_collector.analyze_social_presence(
                nonprofit.name, social_accounts
            )
            logger.info(f"Analyzed social media for {nonprofit.name}")
        
        # Update analysis
        nonprofit.mission_alignment = ranking_engine.mission_analyzer.analyze_alignment(nonprofit)
        nonprofit.partnership_roi = ranking_engine.roi_calculator.calculate_roi(nonprofit)
        nonprofit.data_quality_score = calculate_data_quality(nonprofit)
        
        logger.info(f"Deep analysis completed for {nonprofit.name}")
        
    except Exception as e:
        logger.error(f"Deep analysis error for {nonprofit.name}: {e}")


def calculate_data_quality(nonprofit: Nonprofit) -> float:
    """Calculate data quality score based on completeness"""
    score = 0.0
    weights = {
        'mission_statement': 0.2,
        'financial_history': 0.25,
        'programs': 0.15,
        'website': 0.1,
        'social_media': 0.1,
        'leadership': 0.1,
        'address': 0.1
    }
    
    if nonprofit.mission_statement:
        score += weights['mission_statement']
    
    if nonprofit.financial_history:
        score += weights['financial_history'] * min(1.0, len(nonprofit.financial_history) / 3)
    
    if nonprofit.programs:
        score += weights['programs'] * min(1.0, len(nonprofit.programs) / 5)
    
    if nonprofit.website:
        score += weights['website']
    
    if nonprofit.social_media:
        score += weights['social_media'] * min(1.0, len(nonprofit.social_media) / 3)
    
    if nonprofit.leadership:
        score += weights['leadership'] * min(1.0, len(nonprofit.leadership) / 5)
    
    if nonprofit.address and nonprofit.address.street:
        score += weights['address']
    
    return min(1.0, score)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)