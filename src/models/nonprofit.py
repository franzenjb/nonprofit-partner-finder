from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum


class DataSource(Enum):
    IRS_990 = "irs_990"
    WEBSITE = "website"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    GUIDESTAR = "guidestar"
    CHARITY_NAVIGATOR = "charity_navigator"


class NonprofitStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class FinancialData:
    year: int
    total_revenue: float
    total_expenses: float
    total_assets: float
    total_liabilities: float
    net_assets: float
    program_expenses: float
    administrative_expenses: float
    fundraising_expenses: float
    source: DataSource = DataSource.IRS_990
    
    @property
    def program_expense_ratio(self) -> float:
        if self.total_expenses > 0:
            return self.program_expenses / self.total_expenses
        return 0.0
    
    @property
    def overhead_ratio(self) -> float:
        if self.total_expenses > 0:
            overhead = self.administrative_expenses + self.fundraising_expenses
            return overhead / self.total_expenses
        return 0.0


@dataclass
class SocialMediaPresence:
    platform: str
    handle: str
    followers: int
    engagement_rate: float
    last_post_date: Optional[datetime] = None
    verified: bool = False
    sentiment_score: Optional[float] = None


@dataclass
class MissionAlignment:
    score: float  # 0.0 to 1.0
    matched_keywords: List[str]
    service_overlap: Dict[str, float]
    explanation: str
    confidence: float


@dataclass
class PartnershipROI:
    estimated_value: float
    resource_sharing_potential: Dict[str, Any]
    impact_multiplier: float
    cost_savings: float
    reach_expansion: int
    explanation: str


@dataclass
class Nonprofit:
    ein: str  # Employer Identification Number
    name: str
    address: Address
    mission_statement: str
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    year_founded: Optional[int] = None
    status: NonprofitStatus = NonprofitStatus.UNKNOWN
    ntee_code: Optional[str] = None  # National Taxonomy of Exempt Entities
    
    # Data from various sources
    financial_history: List[FinancialData] = field(default_factory=list)
    social_media: List[SocialMediaPresence] = field(default_factory=list)
    programs: List[str] = field(default_factory=list)
    leadership: List[Dict[str, str]] = field(default_factory=list)
    
    # Analysis results
    mission_alignment: Optional[MissionAlignment] = None
    partnership_roi: Optional[PartnershipROI] = None
    overall_score: Optional[float] = None
    ranking: Optional[int] = None
    
    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)
    data_sources: List[DataSource] = field(default_factory=list)
    data_quality_score: float = 0.0
    
    def get_latest_financials(self) -> Optional[FinancialData]:
        if self.financial_history:
            return max(self.financial_history, key=lambda x: x.year)
        return None
    
    def calculate_stability_score(self) -> float:
        if len(self.financial_history) < 2:
            return 0.5
        
        latest = self.get_latest_financials()
        if not latest:
            return 0.5
        
        score = 0.0
        
        # Revenue stability
        if latest.total_revenue > 0:
            score += 0.3
        
        # Asset to liability ratio
        if latest.total_liabilities > 0:
            ratio = latest.total_assets / latest.total_liabilities
            if ratio > 2:
                score += 0.3
            elif ratio > 1:
                score += 0.2
        
        # Program expense ratio
        score += latest.program_expense_ratio * 0.4
        
        return min(score, 1.0)