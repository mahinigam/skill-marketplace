import math
import uuid
from typing import List, Dict, Any, Tuple
from shared.models.models import Finding, RootCause, ReadinessScore, FindingType, ActionRecommendation

def calculate_confidence(evidence_count: int, convergence: bool = False, contradictions: int = 0) -> float:
    base_confidence = min(0.5 + (0.1 * evidence_count), 0.9)
    if convergence:
        base_confidence = min(base_confidence + 0.1, 1.0)
    penalty = 0.2 * contradictions
    return max(0.1, round(base_confidence - penalty, 2))

def calculate_severity(impact: float, breadth: float, confidence: float, importance: float, recoverability_factor: float) -> str:
    # 0.0 to 1.0 scale for inputs
    score = (impact * breadth * confidence * importance * recoverability_factor) * 100
    
    # Matching the 90/70/40 threshold from architectural discussions
    if score >= 90:
        return "critical"
    elif score >= 70:
        return "high"
    elif score >= 40:
        return "medium"
    else:
        return "low"

def fuse_findings(findings: List[Finding]) -> List[Finding]:
    """
    Finding Fusion / False-Positive Firewall: 
    Merge duplicate findings and suppress weak signals.
    """
    fused_map = {}
    for f in findings:
        # Suppress weak signals
        if f.confidence < 0.3 and f.severity in ["low"]:
            continue
            
        # Group by category + title (as a proxy for same issue)
        key = f"{f.category}_{f.title}"
        if key in fused_map:
            existing = fused_map[key]
            existing.affected_pages = list(set(existing.affected_pages + f.affected_pages))
            existing.evidence.extend(f.evidence)
            # Take max confidence
            existing.confidence = max(existing.confidence, f.confidence)
            # Keep highest severity
            severities = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            if severities.get(f.severity, 0) > severities.get(existing.severity, 0):
                existing.severity = f.severity
        else:
            fused_map[key] = f
            
    # For evidence, just keep a sample of max 5 to prevent massive payloads
    for f in fused_map.values():
        if len(f.evidence) > 5:
            f.evidence = f.evidence[:5]
            
    return list(fused_map.values())

def correlate_root_causes(findings: List[Finding]) -> Tuple[List[Finding], List[RootCause]]:
    """
    Clusters findings to find root causes.
    """
    root_causes = []
    
    # Example heuristic: If we have multiple structural defects, they share a template root cause.
    template_defects = [f for f in findings if f.category in ["Discoverability", "Semantics"] and f.severity in ["critical", "high"]]
    
    if len(template_defects) >= 2:
        rc = RootCause(
            id=f"RC-{uuid.uuid4().hex[:6]}",
            title="Global Template Deficiencies",
            description="The underlying page templates fail to expose machine-readable state and routing structures necessary for AI.",
            contributing_findings=[f.id for f in template_defects]
        )
        root_causes.append(rc)
        for f in template_defects:
            f.root_cause_id = rc.id
            
    # Example heuristic: Content freshness missing globally
    freshness_defects = [f for f in findings if f.title == "Missing Freshness Signals"]
    if len(freshness_defects) > 0 and len(freshness_defects[0].affected_pages) > 3:
        rc = RootCause(
            id=f"RC-{uuid.uuid4().hex[:6]}",
            title="Missing Content Lifecycle Data",
            description="Content management system does not surface last-modified or publication dates.",
            contributing_findings=[f.id for f in freshness_defects]
        )
        root_causes.append(rc)
        for f in freshness_defects:
            f.root_cause_id = rc.id
            
    return findings, root_causes

def calculate_readiness_score(findings: List[Finding]) -> ReadinessScore:
    """
    Calculates a dimension-aware AI Readiness Score.
    Starts with 100 per dimension (Discoverability, Semantics, Engagement).
    """
    scores = {"Discoverability": 100, "Semantics": 100, "Engagement": 100}
    
    severity_weights = {"critical": 30, "high": 15, "medium": 5, "low": 1}
    
    # Deduct per dimension
    for f in findings:
        cat = f.category
        if cat not in scores:
            cat = "Discoverability" # fallback
            
        deduction = severity_weights.get(f.severity, 0)
        
        # Diminishing returns penalty (prevent 5 low issues from tanking the score)
        # Using a slight decay based on how many issues are in that category
        scores[cat] -= deduction

    # Normalize to 0-100 per dimension
    for k in scores:
        scores[k] = max(0, min(100, scores[k]))
        
    total_score = int(math.ceil((scores["Discoverability"] * 0.4) + (scores["Semantics"] * 0.4) + (scores["Engagement"] * 0.2)))
    
    return ReadinessScore(
        total=total_score,
        discoverability=scores["Discoverability"],
        semantics=scores["Semantics"],
        engagement=scores["Engagement"]
    )
