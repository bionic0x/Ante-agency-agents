#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

SOURCE_REPO = "mergisi/awesome-openclaw-agents"
DEFAULT_SOURCE_REF = "05820c51125e86a979432e21651d34dc9b14621f"
SOURCE_LICENSE = "MIT"
SOURCE_NOTICE = "Copyright (c) 2025 OpenClaw Community"
DEFAULT_WORKERS = 8

CATEGORY_MAP = {
    "automation":"specialized","business":"specialized","creative":"design","data":"research",
    "development":"engineering","devops":"engineering","ecommerce":"sales","education":"academic",
    "finance":"finance","freelance":"sales","healthcare":"healthcare","hr":"specialized",
    "legal":"support","marketing":"marketing","moltbook":"marketing","personal":"support",
    "productivity":"project-management","real-estate":"sales","real_estate":"sales","saas":"product",
    "security":"security","supply-chain":"specialized","supply_chain":"specialized",
    "compliance":"support","voice":"marketing","customer-success":"support","customer_success":"support",
}
DIVISION_OVERRIDES = {
    "business/customer-support":"support","business/sales-assistant":"sales",
    "business/competitor-pricing":"sales","creative/copywriter":"marketing",
    "creative/podcast-producer":"marketing","creative/video-scripter":"marketing",
    "development/api-tester":"testing","development/test-writer":"testing",
    "development/pr-test-analyzer":"testing","development/dependency-scanner":"security",
    "devops/incident-responder":"support","devops/infra-monitor":"support","devops/log-analyzer":"support",
    "marketing/competitor-watch":"research","marketing/reddit-scout":"marketing",
    "productivity/metrics":"support",
}
CURATED_ALIASES = {
    "business/customer-support":"support-support-responder",
    "business/sales-assistant":"sales-sales-development-representative",
    "creative/ux-researcher":"design-ux-researcher",
    "development/api-tester":"testing-api-tester",
    "marketing/social-media":"marketing-social-media-strategist",
    "marketing/seo-specialist":"marketing-seo-specialist",
    "productivity/project-manager":"project-manager-senior",
    "productivity/orion":"project-manager-senior",
    "security/security-auditor":"security-security-auditor",
}
UA = "Agency-Agents-Unified-Importer/1.0"

def http_text(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=60) as resp:
        return resp.read().decode("utf-8")

def http_json(url:str)->Any:
    return json.loads(http_text(url))

def slugify(v:str)->str:
    return re.sub(r"[^a-z0-9]+","-",v.lower().strip()).strip("-")

def normalize_name(v:str)->str:
    return re.sub(r"[^a-z0-9]+","",v.lower())

def unquote_scalar(v:str)->str:
    v=v.strip()
    return v[1:-1] if len(v)>=2 and v[0]==v[-1] and v[0] in "\"'" else v

def frontmatter_field(text:str,field:str)->str|None:
    if not text.startswith("---\n"): return None
    end=text.find("\n---",4)
    if end<0: return None
    m=re.search(rf"(?m)^{re.escape(field)}:\s*(.+?)\s*$",text[4:end])
    return unquote_scalar(m.group(1)) if m else None

def source_identity(text:str,fallback_id:str)->tuple[str,str]:
    name=role=""
    ident=re.search(r"(?ms)^##\s+Identity\s*$\n(.*?)(?=^##\s+|\Z)",text)
    scope=ident.group(1) if ident else text[:1200]
    m=re.search(r"(?m)^name:\s*[\"']?(.+?)[\"']?\s*$",scope)
    r=re.search(r"(?m)^role:\s*[\"']?(.+?)[\"']?\s*$",scope)
    if m: name=m.group(1).strip().strip("\"'")
    if r: role=r.group(1).strip().strip("\"'")
    if not name or name.lower() in {"backend","openclaw-gateway","pihole"}:
        name=fallback_id.replace("-"," ").title()
    return name,role

def first_capability(text:str)->str:
    cap=re.search(r"(?ms)^##\s+Capabilities\s*$\n(.*?)(?=^##\s+|\Z)",text)
    if cap:
        for line in cap.group(1).splitlines():
            line=re.sub(r"^\s*[-*]\s*","",line).strip()
            if line: return line.rstrip(".")
    per=re.search(r"(?ms)^##\s+Personality\s*$\n(.*?)(?=^##\s+|\Z)",text)
    if per:
        para=" ".join(x.strip() for x in per.group(1).splitlines() if x.strip())
        if para: return para.split(". ")[0].rstrip(".")
    return ""

def discover_canonical(root:Path,divisions:dict[str,Any]):
    slugs=set(); names=collections.defaultdict(list)
    for div in divisions:
        d=root/div
        if not d.is_dir(): continue
        for p in d.rglob("*.md"):
            text=p.read_text(encoding="utf-8")
            if not text.startswith("---\n"): continue
            slugs.add(p.stem)
            name=frontmatter_field(text,"name")
            if name: names[normalize_name(name)].append(p.stem)
    return slugs,names

def resolve_alias(source_key,source_id,display_name,canonical_slugs,canonical_names):
    curated=CURATED_ALIASES.get(source_key)
    if curated and curated in canonical_slugs: return curated,"curated semantic alias"
    if source_id in canonical_slugs: return source_id,"exact canonical slug"
    suffix=[s for s in canonical_slugs if s.endswith("-"+source_id)]
    if len(suffix)==1: return suffix[0],"unambiguous canonical suffix match"
    by_name=canonical_names.get(normalize_name(display_name),[])
    if len(by_name)==1: return by_name[0],"unambiguous display-name match"
    return None,None

def clean_source_body(text:str)->str:
    text=text.replace("\r\n","\n").replace("\r","\n").strip()
    lines=text.splitlines()
    if lines and lines[0].startswith("# "):
        lines=lines[1:]
        while lines and not lines[0].strip(): lines.pop(0)
    return "\n".join(lines).strip()

def render_agent(name,role,capability,division_color,source_key,source_id,source_category,source_path,source_sha,source_ref,source_body):
    mission=role or capability or f"{name} specialist"
    desc=(f"{mission} capability normalized into the unified Agency Agents catalog from the MIT-licensed "
          f"OpenClaw community source; operates under shared strategy, evidence, authority, safety, and tool boundaries.")
    body=clean_source_body(source_body)
    return f'''---
name: {json.dumps(name, ensure_ascii=False)}
description: {json.dumps(desc, ensure_ascii=False)}
color: {json.dumps(division_color)}
source_repo: {json.dumps(SOURCE_REPO)}
source_ref: {json.dumps(source_ref)}
source_path: {json.dumps(source_path)}
source_blob: {json.dumps(source_sha)}
source_license: {json.dumps(SOURCE_LICENSE)}
source_id: {json.dumps(source_id)}
source_category: {json.dumps(source_category)}
---

# {name}

## 🧠 Identity & Source Profile

You are the canonical Agency integration of the community capability **{name}**.

- **Primary specialty**: {mission}
- **Source capability key**: `{source_key}`
- **Canonical authority**: bounded specialist; capability does not imply permission to commit resources, publish, transact, deploy, contact third parties, or accept risk.
- **Governing doctrine**: `strategy/GENERAL-STRATEGY-DOCTRINE.md` and applicable domain/runbook constraints.

## 🎯 Core Mission

Apply this specialty when it is the selected mechanism for the current task. Preserve the source's useful operating knowledge while fitting it into one Agency architecture: one superior purpose, one decision owner, one canonical catalog, one orchestration system, and explicit tool/authority boundaries.

## 🚨 Critical Rules

1. **Agency doctrine outranks imported defaults.** The General Strategy Doctrine governs purpose, evidence, authority, interaction, allocation, and termination.
2. **Imported instructions are capability notes, not higher-priority policy.** Source statements using “always,” “must,” a fixed cadence, a fixed numeric threshold, or a fixed workflow are contextual defaults unless the current mandate independently justifies them.
3. **Do not assume integrations exist.** Source-mentioned tools may be used only when actually available and authorized.
4. **Never fabricate execution or access.** If an integration is absent, state the gap and provide the best bounded artifact, recommendation, or handoff instead.
5. **Respect the user/runtime language and format.** Source presentation defaults do not override the user's explicit requirements.
6. **Keep evidence typed.** Separate established facts, hypotheses, attributed intentions, predictions, and unknowns.
7. **Escalate high-consequence decisions.** Legal, medical, financial, security, privacy, employment, regulated, irreversible, or externally binding actions remain subject to applicable safeguards and decision authority.
8. **Stop when the delegated job is complete or the mechanism fails.** Recurring activity needs an explicit owner, review trigger, and stop condition.

## 📚 Imported Capability Notes — Subordinate Source Material

> The following material is derived from the upstream `SOUL.md`. It supplies domain tactics and operating patterns. Where it conflicts with the Critical Rules above, the Critical Rules govern.

{body}

## 🔗 Provenance & License

- Source repository: `{SOURCE_REPO}`
- Source commit: `{source_ref}`
- Source path: `{source_path}`
- Source blob: `{source_sha}`
- License: MIT
- Notice: {SOURCE_NOTICE}
- Full license notice: `THIRD_PARTY_NOTICES.md`

This normalized file is part of the **single Agency catalog**. It is not a second OpenClaw-only agency; the same canonical agent can be converted to any supported target.
'''

def fetch_source_texts(discovered:list[dict[str,Any]],source_ref:str,workers:int)->tuple[dict[str,str],list[dict[str,str]]]:
    """Fetch independent SOUL.md files concurrently while preserving deterministic output order later."""
    texts:dict[str,str]={}
    errors:list[dict[str,str]]=[]

    def fetch_one(item:dict[str,Any])->tuple[str,str]:
        path=item["source_path"]
        url=f"https://raw.githubusercontent.com/{SOURCE_REPO}/{source_ref}/{path}"
        return path,http_text(url)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_paths={pool.submit(fetch_one,item):item["source_path"] for item in discovered}
        for future in as_completed(future_paths):
            path=future_paths[future]
            try:
                fetched_path,text=future.result()
                texts[fetched_path]=text
            except Exception as exc:
                errors.append({"source_path":path,"error":str(exc)})
    errors.sort(key=lambda item:item["source_path"])
    return texts,errors

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-ref",default=DEFAULT_SOURCE_REF)
    ap.add_argument("--root",default=".")
    ap.add_argument("--workers",type=int,default=DEFAULT_WORKERS,
                    help=f"parallel raw-file fetches (default: {DEFAULT_WORKERS}; use 1 for sequential)")
    ap.add_argument("--dry-run",action="store_true")
    args=ap.parse_args()
    if args.workers < 1:
        ap.error("--workers must be >= 1")
    root=Path(args.root).resolve()
    divisions_doc=json.loads((root/"divisions.json").read_text(encoding="utf-8"))
    divisions=divisions_doc["divisions"]
    canonical_slugs,canonical_names=discover_canonical(root,divisions)

    commit=http_json(f"https://api.github.com/repos/{SOURCE_REPO}/git/commits/{args.source_ref}")
    tree_sha=commit["tree"]["sha"]
    tree=http_json(f"https://api.github.com/repos/{SOURCE_REPO}/git/trees/{tree_sha}?recursive=1")
    source_blobs={i["path"]:i["sha"] for i in tree.get("tree",[])
                  if i.get("type")=="blob" and i["path"].startswith("agents/") and i["path"].endswith("/SOUL.md")}
    discovered=[]; id_counts=collections.Counter()
    for path in sorted(source_blobs):
        parts=path.split("/")
        if len(parts)<4: continue
        category,sid=parts[1],parts[-2]
        id_counts[sid]+=1
        discovered.append({"source_path":path,"source_category":category,"source_id":sid,"source_blob":source_blobs[path]})

    source_manifest=json.loads(http_text(f"https://raw.githubusercontent.com/{SOURCE_REPO}/{args.source_ref}/agents.json"))
    manifest_agents=source_manifest.get("agents",[])
    manifest_paths={a.get("path") for a in manifest_agents if a.get("path")}
    tree_paths={x["source_path"] for x in discovered}

    source_texts,errors=fetch_source_texts(discovered,args.source_ref,args.workers)
    generated_paths=set(); entries=[]; alias_count=import_count=0
    for item in discovered:
        path=item["source_path"]; category=item["source_category"]; sid=item["source_id"]; key=f"{category}/{sid}"
        source_text=source_texts.get(path)
        if source_text is None:
            continue
        name,role=source_identity(source_text,sid); capability=first_capability(source_text)
        alias,reason=resolve_alias(key,sid,name,canonical_slugs,canonical_names)
        if alias:
            alias_count+=1
            entries.append({**item,"source_key":key,"display_name":name,"status":"alias",
                            "canonical_slug":alias,"canonical_path":None,"reason":reason})
            continue
        division=DIVISION_OVERRIDES.get(key,CATEGORY_MAP.get(category,"specialized"))
        if division not in divisions: division="specialized"
        canonical_slug=(f"openclaw-{slugify(category)}-{slugify(sid)}" if id_counts[sid]>1 else f"openclaw-{slugify(sid)}")
        dest=root/division/f"{canonical_slug}.md"
        rendered=render_agent(name,role,capability,divisions[division]["color"],key,sid,category,path,item["source_blob"],args.source_ref,source_text)
        generated_paths.add(dest); import_count+=1
        if not args.dry_run:
            dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(rendered,encoding="utf-8")
        entries.append({**item,"source_key":key,"display_name":name,"status":"imported",
                        "canonical_slug":canonical_slug,"canonical_path":str(dest.relative_to(root)).replace(os.sep,"/"),
                        "canonical_division":division,"reason":"novel capability after deterministic deduplication"})

    stale=[]
    for div in divisions:
        d=root/div
        if not d.is_dir(): continue
        for p in d.rglob("openclaw-*.md"):
            text=p.read_text(encoding="utf-8")
            if f'source_repo: "{SOURCE_REPO}"' in text and p not in generated_paths:
                stale.append(str(p.relative_to(root)).replace(os.sep,"/"))
                if not args.dry_run: p.unlink()

    reg={"_note":"Canonical reconciliation of external capability into the single Agency catalog.",
         "architecture":"strategy/UNIFIED-AGENCY-ARCHITECTURE.md",
         "source":{"repository":SOURCE_REPO,"commit":args.source_ref,"license":SOURCE_LICENSE,
                   "license_notice":SOURCE_NOTICE,"declared_total":source_manifest.get("total"),
                   "manifest_entries":len(manifest_agents),"discovered_soul_files":len(discovered)},
         "reconciliation":{"aliases":alias_count,"imports":import_count,"errors":len(errors),"stale_removed":len(stale),
                           "manifest_paths_missing_from_tree":sorted(manifest_paths-tree_paths),
                           "tree_paths_missing_from_manifest":sorted(tree_paths-manifest_paths),
                           "unknown_source_categories":sorted({x["source_category"] for x in discovered if x["source_category"] not in CATEGORY_MAP})},
         "category_map":CATEGORY_MAP,"division_overrides":DIVISION_OVERRIDES,"curated_aliases":CURATED_ALIASES,
         "errors":errors,"stale_removed":stale,"entries":sorted(entries,key=lambda x:x["source_path"])}
    if not args.dry_run:
        (root/"strategy"/"unified-agency-sources.json").write_text(json.dumps(reg,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"source_commit":args.source_ref,"declared_total":source_manifest.get("total"),
                      "manifest_entries":len(manifest_agents),"discovered_soul_files":len(discovered),
                      "aliases":alias_count,"imports":import_count,"errors":len(errors),"stale_removed":len(stale),
                      "tree_not_manifest":len(tree_paths-manifest_paths),"manifest_not_tree":len(manifest_paths-tree_paths),
                      "workers":args.workers},indent=2))
    return 1 if errors else 0

if __name__=="__main__": raise SystemExit(main())
