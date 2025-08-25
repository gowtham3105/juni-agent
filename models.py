from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class LinkageDecision(str, Enum):
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"

class OutcomeType(str, Enum):
    ALLEGATION = "allegation"
    INVESTIGATION = "investigation"
    CHARGED = "charged"
    CONVICTED = "convicted"
    ACQUITTED = "acquitted"
    SETTLED = "settled"
    REGULATOR_ORDER = "regulator_order"
    NONE = "none"

class CategoryType(str, Enum):
    CORRUPTION = "corruption"
    FRAUD = "fraud"
    MONEY_LAUNDERING = "money_laundering"
    TERRORIST_FINANCING = "terrorist_financing"
    TRAFFICKING = "trafficking"
    SANCTIONS_EVASION = "sanctions_evasion"
    VIOLENCE = "violence"
    REGULATORY = "regulatory"
    CIVIL = "civil"
    NONE = "none"

class HitType(str, Enum):
    ADVERSE_MEDIA = "adverse_media"
    PEP = "pep"
    WATCHLIST = "watchlist"
    SANCTIONS = "sanctions"

class UserProfile(BaseModel):
    """User profile containing identity information"""
    full_name: str
    date_of_birth: Optional[str] = None  # Format: YYYY-MM-DD
    city: Optional[str] = None
    employer: Optional[str] = None
    id_data: Optional[Dict[str, str]] = None  # passport, national ID, etc.
    aliases: List[str] = Field(default_factory=list)
    
class MediaHit(BaseModel):
    """Adverse media hit from vendor"""
    title: str
    snippet: Optional[str] = None
    full_text: Optional[str] = None
    date: str  # Article date
    source: str  # Publisher
    url: Optional[str] = None
    hit_type: HitType = HitType.ADVERSE_MEDIA

class IdentityAnchor(BaseModel):
    """Extracted identity anchor from article"""
    anchor_type: str  # employer, city, dob, age, title, id
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: str  # Where it was extracted from

class AnchorVerification(BaseModel):
    """Result of verifying an anchor against user profile"""
    anchor: IdentityAnchor
    matches: bool
    conflict: bool
    rationale: str

class ArticleAnalysis(BaseModel):
    """Complete analysis of a single article"""
    hit: MediaHit
    brief_summary: str  # 1-line neutral paraphrase
    anchors: List[IdentityAnchor]
    anchor_verifications: List[AnchorVerification]
    contradictions: List[str]
    linkage_decision: LinkageDecision
    outcome_type: OutcomeType
    category_type: CategoryType
    credibility_note: str
    recency_note: str
    rationale: str  # 3-line rationale as per SOP
    
class ComplianceResult(BaseModel):
    """Final compliance check result"""
    user_profile: UserProfile
    total_hits: int
    analyzed_articles: List[ArticleAnalysis]
    matched_hits: List[ArticleAnalysis]
    non_matched_hits: List[ArticleAnalysis]
    final_decision: str  # clear/escalate/decline
    decision_score: int  # 0-100
    overall_rationale: str
    targeted_ask: Optional[str] = None
    final_memo: str
    processing_timestamp: datetime = Field(default_factory=datetime.now)
