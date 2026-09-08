import math
import uuid
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from shared.models.models import Finding, RootCause, ReadinessScore, FindingType, ActionRecommendation, FindingCategory

def calculate_confidence(evidence_count: int, convergence: bool = False, contradictions: int = 0) -> float:
    base_confidence = min(0.5 + (0.1 * evidence_count), 0.9)
    if convergence:
        base_confidence = min(base_confidence + 0.1, 1.0)
    penalty = 0.2 * contradictions
    return max(0.1, round(base_confidence - penalty, 2))

def calculate_severity(impact: float, breadth: float, confidence: float, importance: float, recoverability_factor: float) -> str:
    score = (impact * breadth * confidence * importance * recoverability_factor) * 100
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
            
        key = f"{f.category.value}_{f.title}"
        if key in fused_map:
            existing = fused_map[key]
            existing.affected_pages = list(set(existing.affected_pages + f.affected_pages))
            existing.evidence.extend(f.evidence)
            existing.confidence = max(existing.confidence, f.confidence)
            severities = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            if severities.get(f.severity, 0) > severities.get(existing.severity, 0):
                existing.severity = f.severity
        else:
            fused_map[key] = f
            
    for f in fused_map.values():
        if len(f.evidence) > 5:
            f.evidence = f.evidence[:5]
            
    return list(fused_map.values())

def correlate_root_causes(findings: List[Finding]) -> Tuple[List[Finding], List[RootCause]]:
    """
    Clusters findings to find root causes dynamically based on shared mechanisms, pages, or recommendations.
    """
    root_causes = []
    
    # 1. Correlate by Shared Action Recommendation
    action_clusters = defaultdict(list)
    for f in findings:
        # Group by the first 30 chars of the implementation to catch similar actions
        key = f.suggested_action.implementation[:30]
        action_clusters[key].append(f)
        
    for key, group in action_clusters.items():
        if len(group) >= 2:
            rc = RootCause(
                id=f"RC-{uuid.uuid4().hex[:6]}",
                title=f"Systemic issue requiring: {group[0].suggested_action.summary}",
                description=f"Multiple defects trace back to the same missing implementation: {group[0].suggested_action.implementation}",
                contributing_findings=[f.id for f in group]
            )
            root_causes.append(rc)
            for f in group:
                f.root_cause_id = rc.id
                
    # 2. Correlate by Shared Mechanism
    unassigned = [f for f in findings if not f.root_cause_id]
    mech_clusters = defaultdict(list)
    for f in unassigned:
        key = f.mechanism[:50]
        mech_clusters[key].append(f)
        
    for key, group in mech_clusters.items():
        if len(group) >= 2:
            rc = RootCause(
                id=f"RC-{uuid.uuid4().hex[:6]}",
                title="Shared Failure Mechanism",
                description=f"Multiple defects share a failure mechanism: {group[0].mechanism}",
                contributing_findings=[f.id for f in group]
            )
            root_causes.append(rc)
            for f in group:
                f.root_cause_id = rc.id
                
    return findings, root_causes

def calculate_readiness_score(findings: List[Finding]) -> ReadinessScore:
    """
    Calculates a dimension-aware AI Readiness Score using non-linear deduction.
    """
    scores = {FindingCategory.DISCOVERABILITY: 100.0, FindingCategory.SEMANTICS: 100.0, FindingCategory.ENGAGEMENT: 100.0}
    counts = {FindingCategory.DISCOVERABILITY: 0, FindingCategory.SEMANTICS: 0, FindingCategory.ENGAGEMENT: 0}
    
    severity_weights = {"critical": 35.0, "high": 15.0, "medium": 5.0, "low": 1.0}
    
    # Sort findings by severity (critical first) to apply largest deductions early
    sorted_findings = sorted(findings, key=lambda x: severity_weights.get(x.severity, 0), reverse=True)
    
    for f in sorted_findings:
        cat = f.category
        if cat not in scores:
            cat = FindingCategory.DISCOVERABILITY # fallback
            
        base_deduction = severity_weights.get(f.severity, 0)
        
        # Non-linear decay: each subsequent issue in the same category hurts less
        decay_factor = 1.0 / (1.0 + (counts[cat] * 0.5))
        actual_deduction = base_deduction * decay_factor
        
        scores[cat] -= actual_deduction
        counts[cat] += 1

    for k in scores:
        scores[k] = max(0, min(100, int(round(scores[k]))))
        
    total_score = int(math.ceil(
        (scores[FindingCategory.DISCOVERABILITY] * 0.4) + 
        (scores[FindingCategory.SEMANTICS] * 0.4) + 
        (scores[FindingCategory.ENGAGEMENT] * 0.2)
    ))
    
    return ReadinessScore(
        total=total_score,
        discoverability=scores[FindingCategory.DISCOVERABILITY],
        semantics=scores[FindingCategory.SEMANTICS],
        engagement=scores[FindingCategory.ENGAGEMENT]
    )
