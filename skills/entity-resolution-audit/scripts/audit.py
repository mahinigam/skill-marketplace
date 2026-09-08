import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, Entity
from shared.utilities.extractors import extract_json_ld

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    # Track organizations/brands globally
    orgs_found = {}
    
    for url, html in html_cache.items():
        json_blocks = extract_json_ld(html)
        
        for block in json_blocks:
            type_val = block.get('@type', '')
            if type_val in ['Organization', 'Brand', 'LocalBusiness', 'Corporation']:
                name = block.get('name')
                if name:
                    if name not in orgs_found:
                        orgs_found[name] = {
                            "type": type_val,
                            "aliases": block.get('alternateName', []),
                            "sameAs": block.get('sameAs', []),
                            "urls": []
                        }
                    orgs_found[name]["urls"].append(url)
                    
    # Register entities to context
    for name, data in orgs_found.items():
        aliases = data["aliases"] if isinstance(data["aliases"], list) else [data["aliases"]]
        sameAs = data["sameAs"] if isinstance(data["sameAs"], list) else [data["sameAs"]]
        context.entities.append(Entity(
            canonical_name=name,
            aliases=aliases,
            sameAs=sameAs,
            type=data["type"]
        ))
        
    # Analyze Ambiguity
    if len(orgs_found) > 1:
        # e.g., "Apple" vs "Apple Inc." vs "Apple Computers" mapped as distinct entities
        # If they don't share sameAs links, it's ambiguous.
        evidence = []
        affected = []
        for name, data in orgs_found.items():
            affected.extend(data["urls"])
            evidence.append(EvidenceItem(
                source_type="json-ld", 
                url=data["urls"][0], 
                detail=f"Entity candidate: '{name}' (Type: {data['type']}). Lacks robust sameAs linkage." if not data["sameAs"] else f"Entity candidate: '{name}'"
            ))
            
        findings.append(Finding(
            id="ENT-001",
            title="Entity Ambiguity: Multiple Organization Profiles without canonical linkage",
            category="Semantics",
            type=FindingType.DEFECT,
            severity="high",
            confidence=0.9,
            affected_pages=list(set(affected))[:5],
            evidence=evidence,
            mechanism="AI builds knowledge graphs. If multiple distinct nodes represent the same entity without `sameAs` reconciliation, authority is fractured.",
            ai_impact="Loss of brand authority. AI cannot decisively map facts to the brand.",
            suggested_action=ActionRecommendation(
                summary="Unify entities with canonical names and `sameAs` links.",
                priority="P1",
                implementation="Ensure all pages reference the exact same Organization block (same @id, name, and sameAs pointing to Wikidata/LinkedIn).",
                verification="Check that a single Organization entity is extracted site-wide.",
                effort="low",
                expected_impact="high"
            )
        ))
    elif not orgs_found:
        findings.append(Finding(
            id="ENT-002",
            title="Missing Primary Organization Entity",
            category="Semantics",
            type=FindingType.DEFECT,
            severity="medium",
            confidence=0.95,
            affected_pages=[],
            evidence=[],
            mechanism="If the site does not declare who owns it, AI cannot attribute the facts to a brand.",
            ai_impact="Facts are treated as generic claims rather than authoritative brand statements.",
            suggested_action=ActionRecommendation(
                summary="Inject Organization schema on the homepage.",
                priority="P1",
                implementation="Add Organization JSON-LD with logo, name, and sameAs links.",
                verification="Validate Organization schema extraction.",
                effort="low",
                expected_impact="high"
            )
        ))

    context.findings.extend(findings)
    return context
