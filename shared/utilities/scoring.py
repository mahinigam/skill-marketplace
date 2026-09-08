import math
from typing import List, Dict, Any
from shared.models.models import Finding, AuditSummary

def calculate_confidence(evidence_count: int, convergence: bool = False, contradictions: int = 0) -> float:
    """
    Calculates a confidence score between 0.0 and 1.0 based on evidence.
    """
    base_confidence = min(0.5 + (0.1 * evidence_count), 0.9)
    if convergence:
        base_confidence = min(base_confidence + 0.1, 1.0)
    
    penalty = 0.2 * contradictions
    
    return max(0.1, round(base_confidence - penalty, 2))

def calculate_severity(impact: float, breadth: float, confidence: float, importance: float, recoverability_factor: float) -> str:
    """
    Calculates severity based on multiple factors.
    Returns: "critical", "high", "medium", "low"
    """
    # 0.0 to 1.0 scale for inputs
    score = (impact * breadth * confidence * importance * recoverability_factor) * 100
    
    if score >= 80: # adjusted from 90 to be a bit more reasonable
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 30:
        return "medium"
    else:
        return "low"

def summarize_audit(findings: List[Finding]) -> AuditSummary:
    """
    Generates summary metrics and AI Readiness Score from findings.
    """
    summary = AuditSummary(
        total_findings=len(findings),
        critical=sum(1 for f in findings if f.severity == "critical"),
        high=sum(1 for f in findings if f.severity == "high"),
        medium=sum(1 for f in findings if f.severity == "medium"),
        low=sum(1 for f in findings if f.severity == "low"),
        ai_readiness_score=100
    )
    
    # Simple scoring: start at 100, deduct based on severity
    deductions = (summary.critical * 20) + (summary.high * 10) + (summary.medium * 5) + (summary.low * 1)
    summary.ai_readiness_score = max(0, 100 - deductions)
    
    return summary
