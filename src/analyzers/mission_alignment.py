import numpy as np
from typing import Dict, List, Tuple, Optional
import yaml
from pathlib import Path
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re

from src.models.nonprofit import Nonprofit, MissionAlignment


logger = logging.getLogger(__name__)


class MissionAlignmentAnalyzer:
    """
    Analyzes how well a nonprofit's mission aligns with Red Cross objectives
    Uses NLP and semantic similarity for sophisticated matching
    """
    
    def __init__(self, config_path: str = "./config/red_cross_mission.yaml"):
        self.config = self._load_config(config_path)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Pre-compute embeddings for Red Cross mission elements
        self._precompute_embeddings()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load Red Cross mission configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _precompute_embeddings(self):
        """Pre-compute embeddings for Red Cross mission keywords"""
        # Combine all keywords
        all_keywords = (
            self.config['mission_keywords']['primary'] +
            self.config['mission_keywords']['secondary'] +
            self.config['mission_keywords']['tertiary']
        )
        
        # Create embeddings
        self.keyword_embeddings = self.model.encode(all_keywords)
        self.keywords = all_keywords
        
        # Create service category embeddings
        service_descriptions = []
        for category, details in self.config['service_categories'].items():
            service_descriptions.append(f"{category}: {', '.join(details['subcategories'])}")
        
        self.service_embeddings = self.model.encode(service_descriptions)
        self.service_categories = list(self.config['service_categories'].keys())
    
    def analyze_alignment(self, nonprofit: Nonprofit) -> MissionAlignment:
        """
        Comprehensive mission alignment analysis
        """
        # Combine all text about the nonprofit
        nonprofit_text = self._compile_nonprofit_text(nonprofit)
        
        # Calculate various alignment scores
        keyword_score, matched_keywords = self._keyword_matching(nonprofit_text)
        semantic_score = self._semantic_similarity(nonprofit_text)
        service_overlap = self._service_category_overlap(nonprofit)
        program_alignment = self._program_alignment(nonprofit)
        
        # Calculate weighted overall score
        weights = self.config['scoring_weights']
        overall_score = (
            weights['mission_alignment'] * semantic_score +
            weights['service_overlap'] * np.mean(list(service_overlap.values())) +
            weights['geographic_coverage'] * self._geographic_alignment(nonprofit) +
            weights['organizational_capacity'] * self._capacity_score(nonprofit) +
            weights['partnership_history'] * self._partnership_potential(nonprofit)
        )
        
        # Generate explanation
        explanation = self._generate_explanation(
            nonprofit, keyword_score, semantic_score, 
            service_overlap, matched_keywords
        )
        
        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(nonprofit)
        
        return MissionAlignment(
            score=min(1.0, overall_score),
            matched_keywords=matched_keywords,
            service_overlap=service_overlap,
            explanation=explanation,
            confidence=confidence
        )
    
    def _compile_nonprofit_text(self, nonprofit: Nonprofit) -> str:
        """Compile all text data about the nonprofit"""
        text_parts = [
            nonprofit.mission_statement,
            ' '.join(nonprofit.programs),
            nonprofit.name
        ]
        
        # Add leadership titles (they indicate focus areas)
        for leader in nonprofit.leadership:
            text_parts.append(leader.get('title', ''))
        
        return ' '.join(filter(None, text_parts))
    
    def _keyword_matching(self, text: str) -> Tuple[float, List[str]]:
        """Match keywords with weighted scoring"""
        text_lower = text.lower()
        matched_keywords = []
        score = 0.0
        
        # Check primary keywords (highest weight)
        for keyword in self.config['mission_keywords']['primary']:
            if keyword.lower() in text_lower:
                matched_keywords.append(keyword)
                score += 1.0
        
        # Check secondary keywords
        for keyword in self.config['mission_keywords']['secondary']:
            if keyword.lower() in text_lower:
                matched_keywords.append(keyword)
                score += 0.7
        
        # Check tertiary keywords
        for keyword in self.config['mission_keywords']['tertiary']:
            if keyword.lower() in text_lower:
                matched_keywords.append(keyword)
                score += 0.4
        
        # Normalize score
        max_possible = len(self.config['mission_keywords']['primary']) * 1.0
        normalized_score = min(1.0, score / max_possible) if max_possible > 0 else 0
        
        return normalized_score, matched_keywords
    
    def _semantic_similarity(self, text: str) -> float:
        """Calculate semantic similarity using sentence embeddings"""
        if not text:
            return 0.0
        
        # Encode nonprofit text
        text_embedding = self.model.encode([text])
        
        # Calculate similarity with Red Cross mission keywords
        keyword_similarities = cosine_similarity(text_embedding, self.keyword_embeddings)
        
        # Take top 5 similarities and average them
        top_similarities = np.sort(keyword_similarities[0])[-5:]
        avg_similarity = np.mean(top_similarities)
        
        # Scale to 0-1 range (similarities are usually 0.2-0.8)
        scaled_score = (avg_similarity - 0.2) / 0.6
        
        return max(0.0, min(1.0, scaled_score))
    
    def _service_category_overlap(self, nonprofit: Nonprofit) -> Dict[str, float]:
        """Analyze overlap in service categories"""
        overlap = {}
        nonprofit_text = self._compile_nonprofit_text(nonprofit).lower()
        
        for category, details in self.config['service_categories'].items():
            score = 0.0
            matches = 0
            
            # Check subcategories
            for subcategory in details['subcategories']:
                if subcategory.replace('_', ' ') in nonprofit_text:
                    matches += 1
            
            if len(details['subcategories']) > 0:
                score = matches / len(details['subcategories'])
            
            # Apply category weight
            overlap[category] = score * details['weight']
        
        return overlap
    
    def _program_alignment(self, nonprofit: Nonprofit) -> float:
        """Analyze how well programs align with Red Cross activities"""
        if not nonprofit.programs:
            return 0.5  # Neutral score if no program data
        
        # Encode programs
        program_text = ' '.join(nonprofit.programs)
        program_embedding = self.model.encode([program_text])
        
        # Compare with service category embeddings
        similarities = cosine_similarity(program_embedding, self.service_embeddings)
        
        # Return maximum similarity
        return float(np.max(similarities))
    
    def _geographic_alignment(self, nonprofit: Nonprofit) -> float:
        """Score geographic coverage alignment"""
        # This would check if the nonprofit operates in areas where Red Cross needs partners
        # For now, return a default score
        return 0.7
    
    def _capacity_score(self, nonprofit: Nonprofit) -> float:
        """Evaluate organizational capacity"""
        score = 0.5  # Base score
        
        # Check financial stability
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials:
            # Revenue size bonus
            if latest_financials.total_revenue > 1000000:
                score += 0.2
            elif latest_financials.total_revenue > 100000:
                score += 0.1
            
            # Efficiency bonus
            if latest_financials.program_expense_ratio > 0.75:
                score += 0.2
            elif latest_financials.program_expense_ratio > 0.65:
                score += 0.1
        
        # Active social media bonus
        if nonprofit.social_media:
            active_accounts = sum(1 for sm in nonprofit.social_media if sm.followers > 100)
            score += min(0.1, active_accounts * 0.02)
        
        return min(1.0, score)
    
    def _partnership_potential(self, nonprofit: Nonprofit) -> float:
        """Evaluate potential for successful partnership"""
        # This would check past partnerships, collaborative indicators, etc.
        # For now, use stability score as proxy
        return nonprofit.calculate_stability_score()
    
    def _calculate_confidence(self, nonprofit: Nonprofit) -> float:
        """Calculate confidence in the alignment score"""
        confidence = 0.0
        
        # Data completeness checks
        if nonprofit.mission_statement:
            confidence += 0.3
        if nonprofit.programs:
            confidence += 0.2
        if nonprofit.financial_history:
            confidence += 0.2
        if nonprofit.website:
            confidence += 0.1
        if nonprofit.social_media:
            confidence += 0.1
        if nonprofit.leadership:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_explanation(self, nonprofit: Nonprofit, keyword_score: float,
                            semantic_score: float, service_overlap: Dict[str, float],
                            matched_keywords: List[str]) -> str:
        """Generate human-readable explanation of the alignment score"""
        explanation_parts = []
        
        # Overall assessment
        overall_score = nonprofit.mission_alignment.score if nonprofit.mission_alignment else 0
        if overall_score > 0.8:
            explanation_parts.append(f"Strong alignment with Red Cross mission ({overall_score:.1%})")
        elif overall_score > 0.6:
            explanation_parts.append(f"Good alignment with Red Cross mission ({overall_score:.1%})")
        elif overall_score > 0.4:
            explanation_parts.append(f"Moderate alignment with Red Cross mission ({overall_score:.1%})")
        else:
            explanation_parts.append(f"Limited alignment with Red Cross mission ({overall_score:.1%})")
        
        # Keywords matched
        if matched_keywords:
            explanation_parts.append(f"Matched keywords: {', '.join(matched_keywords[:5])}")
        
        # Service overlap
        top_services = sorted(service_overlap.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_services and top_services[0][1] > 0:
            service_list = [f"{svc[0].replace('_', ' ')} ({svc[1]:.0%})" 
                          for svc in top_services if svc[1] > 0]
            if service_list:
                explanation_parts.append(f"Service overlap in: {', '.join(service_list)}")
        
        # Semantic similarity insight
        if semantic_score > 0.7:
            explanation_parts.append("Mission statement shows strong thematic alignment")
        elif semantic_score > 0.5:
            explanation_parts.append("Mission statement shows moderate thematic alignment")
        
        # Financial insight
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials and latest_financials.program_expense_ratio > 0.75:
            explanation_parts.append(
                f"Efficient operations ({latest_financials.program_expense_ratio:.0%} to programs)"
            )
        
        return ". ".join(explanation_parts)