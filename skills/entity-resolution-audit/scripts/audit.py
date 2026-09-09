import sys
import os
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from shared.models.models import AuditContext, Finding, EvidenceItem, ActionRecommendation, FindingType, Entity, FindingCategory
from shared.utilities.extractors import extract_json_ld

def run_audit(context: AuditContext, html_cache: dict) -> AuditContext:
    findings = []
    
    # Track organizations/brands globally
    orgs_found = {}
    
    for url, html in html_cache.items():
        json_blocks = extract_json_ld(html)
        found_in_json = False
        
        for block in json_blocks:
            type_val = block.get('@type', '')
            if type_val in ['Organization', 'Brand', 'LocalBusiness', 'Corporation']:
                name = block.get('name')
                if name:
                    found_in_json = True
                    if name not in orgs_found:
                        orgs_found[name] = {
                            "type": type_val,
                            "aliases": block.get('alternateName', []),
                            "sameAs": block.get('sameAs', []),
                            "urls": [],
                            "source": "json-ld"
                        }
                    orgs_found[name]["urls"].append(url)
                    
        # Fallback to HTML Title / H1 extraction if JSON-LD missing
        if not found_in_json:
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string if soup.title else ""
            h1 = soup.find('h1')
            h1_text = h1.get_text(strip=True) if h1 else ""
            
            # Tight heuristic: "Page Title | Brand Name" or logo alt text.
            # Do NOT fallback to H1, as H1 is often a tagline (e.g. "Command your craft").
            name_candidate = None
            if "|" in title:
                cand = title.split("|")[-1].strip()
                if len(cand.split()) <= 4:
                    name_candidate = cand
            elif "-" in title:
                cand = title.split("-")[-1].strip()
                if len(cand.split()) <= 4:
                    name_candidate = cand
            
            if not name_candidate:
                logo = soup.find('img', alt=True)
                if logo and ('logo' in logo.get('class', []) or 'logo' in logo.get('src', '').lower()):
                    if logo['alt'] and len(logo['alt'].split()) <= 4:
                        name_candidate = logo['alt'].replace('Logo', '').replace('logo', '').strip()
                
            if name_candidate:
                if name_candidate not in orgs_found:
                    orgs_found[name_candidate] = {
                        "type": "Organization (Inferred)",
                        "aliases": [],
                        "sameAs": [],
                        "urls": [],
                        "source": "html-fallback"
                    }
                orgs_found[name_candidate]["urls"].append(url)
                
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
        evidence = []
        affected = []
        for name, data in orgs_found.items():
            affected.extend(data["urls"])
            evidence.append(EvidenceItem(
                source_type=data["source"], 
                url=data["urls"][0], 
                detail=f"Entity candidate: '{name}' (Type: {data['type']}). Lacks robust sameAs linkage." if not data["sameAs"] else f"Entity candidate: '{name}'"
            ))
            
        findings.append(Finding(
            id="ENT-001",
            title="Entity Ambiguity: Multiple Organization Profiles without canonical linkage",
            category=FindingCategory.SEMANTICS,
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
    elif not orgs_found or all(d["source"] == "html-fallback" for d in orgs_found.values()):
        evidence = []
        if orgs_found:
            for name, data in orgs_found.items():
                evidence.append(EvidenceItem(source_type="html", url=data["urls"][0], detail=f"Inferred entity '{name}' from title/H1. No structured JSON-LD found."))
                
        findings.append(Finding(
            id="ENT-002",
            title="Missing Primary Structured Organization Entity",
            category=FindingCategory.SEMANTICS,
            type=FindingType.DEFECT,
            severity="medium",
            confidence=0.95,
            affected_pages=[],
            evidence=evidence,
            mechanism="If the site does not declare who owns it explicitly in JSON-LD, AI relies on fragile heuristics.",
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
