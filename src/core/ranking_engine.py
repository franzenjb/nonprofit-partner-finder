import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass
import pandas as pd

from src.models.nonprofit import Nonprofit
from src.analyzers.mission_alignment import MissionAlignmentAnalyzer
from src.analyzers.roi_calculator import PartnershipROICalculator


logger = logging.getLogger(__name__)


@dataclass
class RankingCriteria:
    """Configurable ranking criteria"""
    mission_weight: float = 0.35
    roi_weight: float = 0.25
    stability_weight: float = 0.15
    capacity_weight: float = 0.15
    data_quality_weight: float = 0.10


class NonprofitRankingEngine:
    """
    Ranks nonprofits based on multiple criteria for Red Cross partnership potential
    """
    
    def __init__(self, criteria: RankingCriteria = None):
        self.criteria = criteria or RankingCriteria()
        self.mission_analyzer = MissionAlignmentAnalyzer()
        self.roi_calculator = PartnershipROICalculator()
    
    def rank_nonprofits(self, nonprofits: List[Nonprofit], 
                       zip_code: str = None) -> List[Nonprofit]:
        """
        Rank nonprofits based on comprehensive scoring
        """
        if not nonprofits:
            return []
        
        # Analyze and score each nonprofit
        scored_nonprofits = []
        for nonprofit in nonprofits:
            try:
                # Calculate mission alignment
                nonprofit.mission_alignment = self.mission_analyzer.analyze_alignment(nonprofit)
                
                # Calculate ROI
                nonprofit.partnership_roi = self.roi_calculator.calculate_roi(nonprofit)
                
                # Calculate overall score
                overall_score = self._calculate_overall_score(nonprofit)
                nonprofit.overall_score = overall_score
                
                scored_nonprofits.append(nonprofit)
                
            except Exception as e:
                logger.error(f"Error scoring nonprofit {nonprofit.name}: {e}")
                nonprofit.overall_score = 0
                scored_nonprofits.append(nonprofit)
        
        # Sort by score (highest first)
        scored_nonprofits.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Assign rankings
        for rank, nonprofit in enumerate(scored_nonprofits, 1):
            nonprofit.ranking = rank
        
        return scored_nonprofits
    
    def _calculate_overall_score(self, nonprofit: Nonprofit) -> float:
        """
        Calculate weighted overall score
        """
        scores = {}
        
        # Mission alignment score
        if nonprofit.mission_alignment:
            scores['mission'] = nonprofit.mission_alignment.score
        else:
            scores['mission'] = 0
        
        # ROI score (normalize to 0-1)
        if nonprofit.partnership_roi:
            roi_ratio = nonprofit.partnership_roi.estimated_value / 100000  # Normalize by $100k
            scores['roi'] = min(1.0, roi_ratio)
        else:
            scores['roi'] = 0
        
        # Stability score
        scores['stability'] = nonprofit.calculate_stability_score()
        
        # Capacity score
        scores['capacity'] = self._calculate_capacity_score(nonprofit)
        
        # Data quality score
        scores['data_quality'] = nonprofit.data_quality_score
        
        # Apply weights
        weighted_score = (
            scores['mission'] * self.criteria.mission_weight +
            scores['roi'] * self.criteria.roi_weight +
            scores['stability'] * self.criteria.stability_weight +
            scores['capacity'] * self.criteria.capacity_weight +
            scores['data_quality'] * self.criteria.data_quality_weight
        )
        
        return weighted_score
    
    def _calculate_capacity_score(self, nonprofit: Nonprofit) -> float:
        """
        Calculate organizational capacity score
        """
        score = 0.5  # Base score
        
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials:
            # Size bonus
            if latest_financials.total_revenue > 5000000:
                score += 0.2
            elif latest_financials.total_revenue > 1000000:
                score += 0.15
            elif latest_financials.total_revenue > 100000:
                score += 0.1
            
            # Efficiency bonus
            if latest_financials.program_expense_ratio > 0.8:
                score += 0.2
            elif latest_financials.program_expense_ratio > 0.7:
                score += 0.1
            
            # Growth indicator
            if len(nonprofit.financial_history) >= 3:
                revenues = [f.total_revenue for f in nonprofit.financial_history[-3:]]
                if all(revenues[i] <= revenues[i+1] for i in range(len(revenues)-1)):
                    score += 0.1  # Consistent growth
        
        return min(1.0, score)
    
    def get_top_partners(self, nonprofits: List[Nonprofit], 
                        top_n: int = 10,
                        min_score: float = 0.5) -> List[Nonprofit]:
        """
        Get top N nonprofits that meet minimum score threshold
        """
        ranked = self.rank_nonprofits(nonprofits)
        
        # Filter by minimum score
        qualified = [np for np in ranked if np.overall_score >= min_score]
        
        # Return top N
        return qualified[:top_n]
    
    def generate_ranking_report(self, nonprofits: List[Nonprofit]) -> pd.DataFrame:
        """
        Generate detailed ranking report as DataFrame
        """
        data = []
        
        for np in nonprofits:
            row = {
                'Rank': np.ranking,
                'Name': np.name,
                'EIN': np.ein,
                'Overall Score': f"{np.overall_score:.1%}" if np.overall_score else "0%",
                'Mission Alignment': f"{np.mission_alignment.score:.1%}" if np.mission_alignment else "N/A",
                'ROI Potential': f"${np.partnership_roi.estimated_value:,.0f}" if np.partnership_roi else "N/A",
                'Stability': f"{np.calculate_stability_score():.1%}",
                'Programs': len(np.programs),
                'Annual Revenue': f"${np.get_latest_financials().total_revenue:,.0f}" if np.get_latest_financials() else "N/A",
                'Efficiency': f"{np.get_latest_financials().program_expense_ratio:.1%}" if np.get_latest_financials() else "N/A"
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        return df
    
    def explain_ranking(self, nonprofit: Nonprofit) -> str:
        """
        Generate detailed explanation for a nonprofit's ranking
        """
        explanation = []
        
        # Header
        explanation.append(f"**{nonprofit.name}** - Rank #{nonprofit.ranking}")
        explanation.append(f"Overall Score: {nonprofit.overall_score:.1%}")
        explanation.append("")
        
        # Mission alignment
        if nonprofit.mission_alignment:
            explanation.append("**Mission Alignment**")
            explanation.append(nonprofit.mission_alignment.explanation)
            explanation.append("")
        
        # ROI potential
        if nonprofit.partnership_roi:
            explanation.append("**Partnership ROI**")
            explanation.append(nonprofit.partnership_roi.explanation)
            explanation.append("")
        
        # Financial stability
        explanation.append("**Financial Stability**")
        stability_score = nonprofit.calculate_stability_score()
        if stability_score > 0.7:
            explanation.append(f"Strong financial stability ({stability_score:.1%})")
        elif stability_score > 0.5:
            explanation.append(f"Moderate financial stability ({stability_score:.1%})")
        else:
            explanation.append(f"Limited financial data available ({stability_score:.1%})")
        
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials:
            explanation.append(f"- Revenue: ${latest_financials.total_revenue:,.0f}")
            explanation.append(f"- Program efficiency: {latest_financials.program_expense_ratio:.1%}")
        explanation.append("")
        
        # Organizational capacity
        explanation.append("**Organizational Capacity**")
        capacity_score = self._calculate_capacity_score(nonprofit)
        if capacity_score > 0.7:
            explanation.append(f"Strong organizational capacity ({capacity_score:.1%})")
        elif capacity_score > 0.5:
            explanation.append(f"Moderate organizational capacity ({capacity_score:.1%})")
        else:
            explanation.append(f"Developing organizational capacity ({capacity_score:.1%})")
        
        if nonprofit.programs:
            explanation.append(f"- {len(nonprofit.programs)} active programs")
        if nonprofit.social_media:
            total_reach = sum(sm.followers for sm in nonprofit.social_media)
            explanation.append(f"- Social media reach: {total_reach:,} followers")
        explanation.append("")
        
        # Data quality note
        if nonprofit.data_quality_score < 0.5:
            explanation.append("*Note: Limited data available may affect ranking accuracy*")
        
        return "\n".join(explanation)
    
    def compare_nonprofits(self, nonprofit1: Nonprofit, 
                          nonprofit2: Nonprofit) -> Dict[str, Any]:
        """
        Compare two nonprofits side by side
        """
        comparison = {
            'nonprofit1': {
                'name': nonprofit1.name,
                'rank': nonprofit1.ranking,
                'overall_score': nonprofit1.overall_score,
                'mission_alignment': nonprofit1.mission_alignment.score if nonprofit1.mission_alignment else 0,
                'roi_potential': nonprofit1.partnership_roi.estimated_value if nonprofit1.partnership_roi else 0,
                'stability': nonprofit1.calculate_stability_score(),
                'programs': len(nonprofit1.programs)
            },
            'nonprofit2': {
                'name': nonprofit2.name,
                'rank': nonprofit2.ranking,
                'overall_score': nonprofit2.overall_score,
                'mission_alignment': nonprofit2.mission_alignment.score if nonprofit2.mission_alignment else 0,
                'roi_potential': nonprofit2.partnership_roi.estimated_value if nonprofit2.partnership_roi else 0,
                'stability': nonprofit2.calculate_stability_score(),
                'programs': len(nonprofit2.programs)
            },
            'recommendation': ''
        }
        
        # Generate recommendation
        if nonprofit1.overall_score > nonprofit2.overall_score:
            diff = (nonprofit1.overall_score - nonprofit2.overall_score) / nonprofit2.overall_score * 100
            comparison['recommendation'] = f"{nonprofit1.name} scores {diff:.0f}% higher overall"
        else:
            diff = (nonprofit2.overall_score - nonprofit1.overall_score) / nonprofit1.overall_score * 100
            comparison['recommendation'] = f"{nonprofit2.name} scores {diff:.0f}% higher overall"
        
        return comparison