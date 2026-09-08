from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class EntityRecord(BaseModel):
    id: str
    name: str
    type: str
    aliases: List[str] = []
    canonical_url: Optional[str] = None
    properties: Dict[str, Any] = {}

class FactRecord(BaseModel):
    id: str
    subject_entity_id: str
    attribute: str
    value: Any
    confidence: float
    source_url: str

class ClaimRecord(BaseModel):
    id: str
    fact_id: str
    claim_text: str
    context: str

class SourceRecord(BaseModel):
    url: str
    type: str # "internal", "external_profile", "external_article"
    last_modified: Optional[datetime] = None

class Signal(BaseModel):
    id: str
    type: str
    source_url: str
    value: Any
    description: str

class EvidenceItem(BaseModel):
    source_type: str # e.g. "html", "rendered_dom", "json_ld", "http_headers"
    url: str
    detail: str
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None

class ActionRecommendation(BaseModel):
    summary: str
    priority: str # "P0", "P1", "P2", "P3"
    implementation: str
    verification: str
    effort: str # "low", "medium", "high"
    expected_impact: str # "low", "medium", "high"

class Finding(BaseModel):
    id: str
    title: str
    category: str
    type: str # "defect", "risk", "observation"
    severity: str # "critical", "high", "medium", "low"
    confidence: float
    evidence: List[EvidenceItem]
    mechanism: Optional[str] = None
    ai_impact: Optional[str] = None
    user_impact: Optional[str] = None
    root_cause: Optional[str] = None
    affected_pages: List[str] = []
    affected_entities: List[str] = []
    suggested_action: Optional[ActionRecommendation] = None

class Opportunity(BaseModel):
    id: str
    title: str
    description: str
    evidence: List[EvidenceItem]
    suggested_action: ActionRecommendation

class PageRecord(BaseModel):
    url: str
    status_code: int
    content_type: str
    size_bytes: int
    robots_allowed: bool
    title: Optional[str] = None
    canonical_url: Optional[str] = None
    importance: str # "P0", "P1", "P2", "P3"
    structured_data: List[Dict[str, Any]] = []

class CrawlRecord(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    pages_visited: int = 0
    pages: Dict[str, PageRecord] = {}
    robots_txt_content: Optional[str] = None
    sitemaps_found: List[str] = []

class AuditTarget(BaseModel):
    url: str
    domain: str

class AuditContext(BaseModel):
    target: AuditTarget
    crawl: CrawlRecord
    entities: Dict[str, EntityRecord] = {}
    facts: Dict[str, FactRecord] = {}
    claims: Dict[str, ClaimRecord] = {}
    sources: Dict[str, SourceRecord] = {}
    signals: List[Signal] = []
    findings: List[Finding] = []
    opportunities: List[Opportunity] = []

class AuditSummary(BaseModel):
    total_findings: int
    critical: int
    high: int
    medium: int
    low: int
    ai_readiness_score: int

class FinalAuditReport(BaseModel):
    site: str
    audited_at: str
    summary: AuditSummary
    findings: List[Finding]
    opportunities: List[Opportunity]
    root_causes: List[str] = []
