import math
import uuid
import re
from typing import List, Dict, Any, Tuple, Set
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


def _tokenize(text: str) -> Set[str]:
    """Extract meaningful keywords from a text string, lowercased."""
    stop_words = {"the", "a", "an", "is", "are", "to", "for", "of", "in", "on", "and", "or", "that", "this", "it", "with", "as", "by"}
    words = set(re.findall(r'[a-z]+', text.lower()))
    return words - stop_words


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _action_verb(action: ActionRecommendation) -> str:
    """Extract the leading verb from an action summary (e.g., 'Add', 'Implement', 'Wrap')."""
    words = action.summary.strip().split()
    return words[0].lower() if words else ""


def correlate_root_causes(findings: List[Finding]) -> Tuple[List[Finding], List[RootCause]]:
    """
    Clusters findings to find root causes using multi-signal correlation:
      - Shared mechanism keywords (tokenized, not prefix)
      - Shared affected pages (Jaccard similarity >= 0.3)
      - Same category
      - Same suggested action verb
    
    A pair of findings must share at least 2 of these 4 signals to be grouped.
    """
    root_causes = []
    n = len(findings)
    if n < 2:
        return findings, root_causes
    
    # Pre-compute per-finding features
    mech_tokens = [_tokenize(f.mechanism) for f in findings]
    page_sets = [set(f.affected_pages) for f in findings]
    categories = [f.category for f in findings]
    action_verbs = [_action_verb(f.suggested_action) for f in findings]
    impl_tokens = [_tokenize(f.suggested_action.implementation) for f in findings]
    
    # Build adjacency: edge between i and j if >=2 signals match
    adjacency = defaultdict(set)
    for i in range(n):
        for j in range(i + 1, n):
            signals_shared = 0
            
            # Signal 1: mechanism keyword overlap (Jaccard >= 0.3)
            if _jaccard_similarity(mech_tokens[i], mech_tokens[j]) >= 0.3:
                signals_shared += 1
                
            # Signal 2: affected page overlap (Jaccard >= 0.3)
            if _jaccard_similarity(page_sets[i], page_sets[j]) >= 0.3:
                signals_shared += 1
                
            # Signal 3: same category
            if categories[i] == categories[j]:
                signals_shared += 1
                
            # Signal 4: same action verb AND implementation keyword overlap
            if action_verbs[i] and action_verbs[i] == action_verbs[j]:
                signals_shared += 1
            elif _jaccard_similarity(impl_tokens[i], impl_tokens[j]) >= 0.4:
                signals_shared += 1
                
            if signals_shared >= 2:
                adjacency[i].add(j)
                adjacency[j].add(i)
    
    # Greedy connected-component clustering
    assigned = set()
    clusters = []
    for i in range(n):
        if i in assigned:
            continue
        if i not in adjacency:
            continue
        # BFS to find the connected component
        cluster = set()
        queue = [i]
        while queue:
            node = queue.pop(0)
            if node in assigned:
                continue
            assigned.add(node)
            cluster.add(node)
            for neighbor in adjacency[node]:
                if neighbor not in assigned:
                    queue.append(neighbor)
        if len(cluster) >= 2:
            clusters.append(cluster)
    
    # Create root causes from clusters
    for cluster in clusters:
        group = [findings[idx] for idx in cluster]
        
        # Determine root cause title from the most common mechanism keywords
        all_mech_tokens = set()
        for idx in cluster:
            all_mech_tokens |= mech_tokens[idx]
        
        # Use the most severe finding's mechanism as the description
        group_sorted = sorted(group, key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.severity, 4))
        primary = group_sorted[0]
        
        rc = RootCause(
            id=f"RC-{uuid.uuid4().hex[:6]}",
            title=f"Systemic: {primary.suggested_action.summary}",
            description=f"Multiple defects ({len(group)}) share a common failure pattern: {primary.mechanism}",
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
            cat = FindingCategory.DISCOVERABILITY  # fallback
            
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
