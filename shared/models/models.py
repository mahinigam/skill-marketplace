from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class FindingType(str, Enum):
    DEFECT = "defect"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    OBSERVATION = "observation"

class FindingCategory(str, Enum):
    DISCOVERABILITY = "Discoverability"
    SEMANTICS = "Semantics"
    ENGAGEMENT = "Engagement"

class Source(BaseModel):
    url: str
    source_type: str # html, json-ld, robots, sitemap, external
    
class EvidenceItem(BaseModel):
    source_type: str
    url: str
    detail: str
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None
    
class Entity(BaseModel):
    canonical_name: str
    aliases: List[str] = []
    sameAs: List[str] = []
    type: str = "Organization" # Organization, Product, Brand, etc.

class Fact(BaseModel):
    subject: str
    predicate: str
    object_value: str
    sources: List[Source] = []

class Claim(BaseModel):
    fact: Fact
    confidence: float
    is_corroborated: bool = False

class Signal(BaseModel):
    name: str
    value: Any
    weight: float = 1.0

class ActionRecommendation(BaseModel):
    summary: str
    priority: str # P0, P1, P2, P3
    implementation: str
    verification: str
    effort: str # low, medium, high
    expected_impact: str # low, medium, high

class RootCause(BaseModel):
    id: str
    title: str
    description: str
    contributing_findings: List[str] = [] # list of Finding IDs

class Finding(BaseModel):
    id: str
    title: str
    category: FindingCategory
    type: FindingType
    severity: str # critical, high, medium, low
    confidence: float
    affected_pages: List[str] = []
    evidence: List[EvidenceItem]
    mechanism: str
    ai_impact: Optional[str] = None
    user_impact: Optional[str] = None
    suggested_action: ActionRecommendation
    root_cause_id: Optional[str] = None

class Opportunity(BaseModel):
    id: str
    title: str
    description: str
    evidence: List[EvidenceItem] = []
    confidence: float
    impact: str # low, medium, high
    priority: str # P0, P1, P2, P3
    suggested_action: ActionRecommendation

class PageRecord(BaseModel):
    url: str
    status_code: int
    content_type: str
    size_bytes: int
    robots_allowed: bool
    title: Optional[str] = None
    canonical_url: Optional[str] = None
    importance_score: float = 0.0
    structured_data: List[Dict[str, Any]] = []

class CrawlRecord(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    pages_crawled: int = 0
    errors: int = 0
    pages: Dict[str, PageRecord] = {}
    sitemap_urls: List[str] = []

class AuditTarget(BaseModel):
    url: str
    domain: str

class ReadinessScore(BaseModel):
    total: int = 0
    discoverability: int = 0
    semantics: int = 0
    engagement: int = 0

class AuditContext(BaseModel):
    target: AuditTarget
    crawl: CrawlRecord
    findings: List[Finding] = []
    opportunities: List[Opportunity] = []
    root_causes: List[RootCause] = []
    entities: List[Entity] = []
    facts: List[Fact] = []
    claims: List[Claim] = []
    signals: List[Signal] = []
    html_pages: Dict[str, str] = {} # Storing fetched HTML

class FinalAuditReport(BaseModel):
    site: str
    audited_at: str
    score: ReadinessScore
    summary: Dict[str, int]
    root_causes: List[RootCause]
    findings: List[Finding]
    opportunities: List[Opportunity]
