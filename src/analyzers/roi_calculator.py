import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

from src.models.nonprofit import Nonprofit, PartnershipROI, FinancialData


logger = logging.getLogger(__name__)


@dataclass
class ROIMetrics:
    """Detailed ROI metrics for partnership evaluation"""
    direct_cost_savings: float
    indirect_cost_savings: float
    resource_sharing_value: float
    reach_expansion_value: float
    capability_enhancement_value: float
    risk_mitigation_value: float
    total_value: float
    investment_required: float
    roi_ratio: float
    payback_period_months: int


class PartnershipROICalculator:
    """
    Calculates expected return on investment for partnerships
    Considers resource sharing, cost savings, and impact multiplication
    """
    
    # Value assumptions (would be configurable in production)
    VOLUNTEER_HOUR_VALUE = 29.95  # Independent Sector 2023 value
    FACILITY_SHARING_VALUE_PER_SQFT = 15.0  # Monthly
    DONOR_LIFETIME_VALUE = 1200.0
    BENEFICIARY_SERVICE_VALUE = 150.0
    
    def __init__(self):
        self.weights = {
            'resource_sharing': 0.25,
            'cost_reduction': 0.20,
            'reach_expansion': 0.20,
            'capability_enhancement': 0.15,
            'sustainability': 0.10,
            'risk_mitigation': 0.10
        }
    
    def calculate_roi(self, nonprofit: Nonprofit, 
                     partnership_type: str = "standard") -> PartnershipROI:
        """
        Calculate comprehensive ROI for potential partnership
        """
        # Get financial baseline
        latest_financials = nonprofit.get_latest_financials()
        if not latest_financials:
            return self._default_roi()
        
        # Calculate various value components
        resource_value = self._calculate_resource_sharing_value(nonprofit, latest_financials)
        cost_savings = self._calculate_cost_savings(nonprofit, latest_financials)
        reach_value = self._calculate_reach_expansion_value(nonprofit)
        capability_value = self._calculate_capability_enhancement(nonprofit)
        risk_value = self._calculate_risk_mitigation_value(nonprofit)
        
        # Calculate total value
        total_value = (
            resource_value['total'] +
            cost_savings['total'] +
            reach_value['total'] +
            capability_value +
            risk_value
        )
        
        # Estimate investment required
        investment = self._estimate_investment_required(nonprofit, partnership_type)
        
        # Calculate ROI metrics
        roi_ratio = (total_value - investment) / investment if investment > 0 else 0
        impact_multiplier = 1 + (roi_ratio * 0.5)  # Conservative multiplier
        
        # Create detailed explanation
        explanation = self._generate_roi_explanation(
            resource_value, cost_savings, reach_value,
            capability_value, risk_value, investment, roi_ratio
        )
        
        return PartnershipROI(
            estimated_value=total_value,
            resource_sharing_potential=resource_value,
            impact_multiplier=impact_multiplier,
            cost_savings=cost_savings['total'],
            reach_expansion=reach_value['new_beneficiaries'],
            explanation=explanation
        )
    
    def _calculate_resource_sharing_value(self, nonprofit: Nonprofit, 
                                         financials: FinancialData) -> Dict:
        """Calculate value from resource sharing opportunities"""
        value = {
            'facilities': 0,
            'volunteers': 0,
            'equipment': 0,
            'expertise': 0,
            'total': 0
        }
        
        # Estimate based on organization size
        org_size_factor = min(1.0, financials.total_revenue / 1000000)
        
        # Facilities sharing (estimate based on budget)
        if financials.total_assets > 500000:
            # Assume 10% of assets are facilities that could be shared
            facility_value = financials.total_assets * 0.1
            # Monthly sharing value
            value['facilities'] = facility_value * 0.02 * 12  # 2% monthly * 12 months
        
        # Volunteer sharing
        # Estimate volunteer base from social media following
        if nonprofit.social_media:
            total_followers = sum(sm.followers for sm in nonprofit.social_media)
            estimated_volunteers = total_followers * 0.01  # 1% conversion
            volunteer_hours = estimated_volunteers * 20  # 20 hours/year each
            value['volunteers'] = volunteer_hours * self.VOLUNTEER_HOUR_VALUE
        
        # Equipment and supplies
        # Estimate from program expenses
        if financials.program_expenses > 0:
            value['equipment'] = financials.program_expenses * 0.05  # 5% could be shared
        
        # Expertise and training
        if nonprofit.programs:
            # Value expertise based on number of programs
            value['expertise'] = len(nonprofit.programs) * 5000  # $5k value per program expertise
        
        value['total'] = sum(v for k, v in value.items() if k != 'total')
        
        return value
    
    def _calculate_cost_savings(self, nonprofit: Nonprofit, 
                              financials: FinancialData) -> Dict:
        """Calculate potential cost savings from partnership"""
        savings = {
            'procurement': 0,
            'marketing': 0,
            'administration': 0,
            'training': 0,
            'technology': 0,
            'total': 0
        }
        
        # Joint procurement savings (3-5% of expenses)
        savings['procurement'] = financials.total_expenses * 0.04
        
        # Shared marketing and outreach
        if financials.fundraising_expenses > 0:
            savings['marketing'] = financials.fundraising_expenses * 0.15
        
        # Administrative efficiency
        if financials.administrative_expenses > 0:
            savings['administration'] = financials.administrative_expenses * 0.10
        
        # Shared training programs
        savings['training'] = 10000 * (financials.total_revenue / 1000000)  # Scale with size
        
        # Technology and systems sharing
        savings['technology'] = 5000 + (financials.total_revenue * 0.001)
        
        savings['total'] = sum(v for k, v in savings.items() if k != 'total')
        
        return savings
    
    def _calculate_reach_expansion_value(self, nonprofit: Nonprofit) -> Dict:
        """Calculate value from expanded reach and impact"""
        reach = {
            'new_beneficiaries': 0,
            'new_donors': 0,
            'geographic_expansion': 0,
            'total': 0
        }
        
        # Estimate current reach from financials
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials and latest_financials.program_expenses > 0:
            # Rough estimate: $150 per beneficiary served
            current_beneficiaries = latest_financials.program_expenses / 150
            
            # Partnership could expand reach by 20-40%
            reach['new_beneficiaries'] = int(current_beneficiaries * 0.3)
            
            # Value of serving new beneficiaries
            beneficiary_value = reach['new_beneficiaries'] * self.BENEFICIARY_SERVICE_VALUE
            
            # New donor acquisition
            reach['new_donors'] = reach['new_beneficiaries'] * 0.05  # 5% become donors
            donor_value = reach['new_donors'] * self.DONOR_LIFETIME_VALUE
            
            # Geographic expansion value
            reach['geographic_expansion'] = beneficiary_value * 0.1
            
            reach['total'] = beneficiary_value + donor_value + reach['geographic_expansion']
        
        return reach
    
    def _calculate_capability_enhancement(self, nonprofit: Nonprofit) -> float:
        """Calculate value from enhanced capabilities"""
        value = 0
        
        # New service capabilities
        if nonprofit.programs:
            # Each complementary program adds value
            value += len(nonprofit.programs) * 8000
        
        # Technology and innovation transfer
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials:
            # Organizations with higher efficiency bring more capability
            if latest_financials.program_expense_ratio > 0.75:
                value += 20000
            elif latest_financials.program_expense_ratio > 0.65:
                value += 10000
        
        # Specialized expertise
        if nonprofit.leadership:
            # Value leadership expertise
            value += len(nonprofit.leadership) * 2000
        
        return value
    
    def _calculate_risk_mitigation_value(self, nonprofit: Nonprofit) -> float:
        """Calculate value from risk mitigation"""
        value = 0
        
        # Service continuity (backup during disasters)
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials:
            # Value of having backup capacity
            value += latest_financials.program_expenses * 0.02
        
        # Diversification value
        stability_score = nonprofit.calculate_stability_score()
        if stability_score > 0.7:
            value += 15000  # Stable partners reduce risk
        elif stability_score > 0.5:
            value += 8000
        
        # Compliance and reputation
        if nonprofit.status == nonprofit.status.ACTIVE:
            value += 5000  # Active status indicates compliance
        
        return value
    
    def _estimate_investment_required(self, nonprofit: Nonprofit, 
                                     partnership_type: str) -> float:
        """Estimate investment required for partnership"""
        investment = 0
        
        # Base partnership setup costs
        base_costs = {
            'standard': 25000,
            'strategic': 50000,
            'merger': 100000
        }
        investment += base_costs.get(partnership_type, 25000)
        
        # Integration costs based on size
        latest_financials = nonprofit.get_latest_financials()
        if latest_financials:
            # Larger organizations require more integration
            size_factor = min(1.0, latest_financials.total_revenue / 5000000)
            investment += 20000 * size_factor
        
        # Training and onboarding
        if nonprofit.programs:
            investment += len(nonprofit.programs) * 1000  # Per program integration
        
        # Technology integration
        investment += 10000  # Base technology costs
        
        # Ongoing coordination (first year)
        investment += 15000  # Staff time for coordination
        
        return investment
    
    def _generate_roi_explanation(self, resource_value: Dict, cost_savings: Dict,
                                 reach_value: Dict, capability_value: float,
                                 risk_value: float, investment: float,
                                 roi_ratio: float) -> str:
        """Generate human-readable ROI explanation"""
        explanation_parts = []
        
        # Overall ROI assessment
        if roi_ratio > 3:
            explanation_parts.append(f"Exceptional ROI potential ({roi_ratio:.1f}x return)")
        elif roi_ratio > 2:
            explanation_parts.append(f"Strong ROI potential ({roi_ratio:.1f}x return)")
        elif roi_ratio > 1:
            explanation_parts.append(f"Positive ROI potential ({roi_ratio:.1f}x return)")
        else:
            explanation_parts.append(f"Limited ROI potential ({roi_ratio:.1f}x return)")
        
        # Top value drivers
        value_drivers = []
        
        if resource_value['total'] > 50000:
            value_drivers.append(f"Resource sharing: ${resource_value['total']:,.0f}")
        
        if cost_savings['total'] > 30000:
            value_drivers.append(f"Cost savings: ${cost_savings['total']:,.0f}")
        
        if reach_value['new_beneficiaries'] > 100:
            value_drivers.append(f"Reach expansion: {reach_value['new_beneficiaries']:,} new beneficiaries")
        
        if value_drivers:
            explanation_parts.append(f"Key value drivers: {', '.join(value_drivers[:3])}")
        
        # Investment perspective
        explanation_parts.append(f"Estimated investment: ${investment:,.0f}")
        
        # Payback period
        if roi_ratio > 0:
            annual_value = resource_value['total'] + cost_savings['total']
            if annual_value > 0:
                payback_months = int((investment / annual_value) * 12)
                explanation_parts.append(f"Payback period: {payback_months} months")
        
        # Strategic benefits
        strategic = []
        
        if capability_value > 20000:
            strategic.append("significant capability enhancement")
        
        if risk_value > 15000:
            strategic.append("strong risk mitigation")
        
        if resource_value['volunteers'] > 20000:
            strategic.append("substantial volunteer network")
        
        if strategic:
            explanation_parts.append(f"Strategic benefits: {', '.join(strategic)}")
        
        return ". ".join(explanation_parts)
    
    def _default_roi(self) -> PartnershipROI:
        """Return default ROI when insufficient data"""
        return PartnershipROI(
            estimated_value=0,
            resource_sharing_potential={},
            impact_multiplier=1.0,
            cost_savings=0,
            reach_expansion=0,
            explanation="Insufficient data for ROI calculation"
        )
    
    def calculate_detailed_metrics(self, nonprofit: Nonprofit) -> ROIMetrics:
        """Calculate detailed ROI metrics for reporting"""
        latest_financials = nonprofit.get_latest_financials()
        if not latest_financials:
            return self._default_metrics()
        
        # Calculate all components
        resource_value = self._calculate_resource_sharing_value(nonprofit, latest_financials)
        cost_savings = self._calculate_cost_savings(nonprofit, latest_financials)
        reach_value = self._calculate_reach_expansion_value(nonprofit)
        capability_value = self._calculate_capability_enhancement(nonprofit)
        risk_value = self._calculate_risk_mitigation_value(nonprofit)
        
        # Direct vs indirect savings
        direct_savings = cost_savings['procurement'] + cost_savings['administration']
        indirect_savings = cost_savings['total'] - direct_savings
        
        # Total value and investment
        total_value = (
            resource_value['total'] + cost_savings['total'] +
            reach_value['total'] + capability_value + risk_value
        )
        investment = self._estimate_investment_required(nonprofit, "standard")
        
        # ROI calculation
        roi_ratio = (total_value - investment) / investment if investment > 0 else 0
        
        # Payback period
        annual_return = resource_value['total'] + cost_savings['total']
        payback_months = int((investment / annual_return) * 12) if annual_return > 0 else 999
        
        return ROIMetrics(
            direct_cost_savings=direct_savings,
            indirect_cost_savings=indirect_savings,
            resource_sharing_value=resource_value['total'],
            reach_expansion_value=reach_value['total'],
            capability_enhancement_value=capability_value,
            risk_mitigation_value=risk_value,
            total_value=total_value,
            investment_required=investment,
            roi_ratio=roi_ratio,
            payback_period_months=payback_months
        )
    
    def _default_metrics(self) -> ROIMetrics:
        """Return default metrics when insufficient data"""
        return ROIMetrics(
            direct_cost_savings=0,
            indirect_cost_savings=0,
            resource_sharing_value=0,
            reach_expansion_value=0,
            capability_enhancement_value=0,
            risk_mitigation_value=0,
            total_value=0,
            investment_required=0,
            roi_ratio=0,
            payback_period_months=999
        )