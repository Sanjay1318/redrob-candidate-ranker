"""
Redrob Hackathon — Intelligent Candidate Ranking System
Architecture: Multi-signal hybrid scorer (TF-IDF semantic + structured feature scoring)
No GPU, no external API calls. Runs on CPU within 5 min for 100K candidates.

Scoring pipeline:
1. Semantic relevance (TF-IDF cosine similarity of candidate text vs JD)
2. Skills match (hard-required skills + bonus skills weighted scoring)
3. Career quality (product co. vs services co., title fit, tenure signals)
4. Behavioral engagement (platform signals: recency, response rate, availability)
5. Disqualifier flags (consulting-only, CV-only, wrong domain, honeypot detection)
6. Location/logistics fit

Final score = weighted sum, then disqualifier multipliers applied.
"""

import json
import csv
import re
import math
import argparse
from datetime import datetime, date
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ─── JOB DESCRIPTION (key concepts extracted) ────────────────────────────────

JD_TEXT = """
Senior AI Engineer founding team Redrob AI Series A talent intelligence platform Pune Noida India.
Production experience embeddings retrieval systems sentence-transformers OpenAI embeddings BGE E5 embedding drift 
index refresh retrieval quality regression. Vector databases hybrid search Pinecone Weaviate Qdrant Milvus 
OpenSearch Elasticsearch FAISS. Strong Python code quality. Evaluation frameworks ranking systems NDCG MRR MAP 
offline online A/B testing recruiter feedback loops. LLM fine-tuning LoRA QLoRA PEFT. Learning to rank 
XGBoost neural. HR tech recruiting tech marketplace products. Distributed systems large scale inference optimization.
Open source contributions AI ML. Scrappy product engineering ship fast iterate learn from users.
Hybrid retrieval dense sparse BM25 re-ranking. Applied ML product companies not pure research.
5-9 years experience applied ML AI roles product companies not services. 
Ranking search recommendation systems real users meaningful scale. 
Strong opinions retrieval evaluation LLM integration fine-tune vs prompt.
NLP information retrieval semantic search candidate job description matching.
Embedding drift vector index production deployment real users.
"""

JD_REQUIRED_SKILLS = [
    "embeddings", "embedding", "sentence-transformers", "sentence transformers",
    "vector database", "vector search", "hybrid search", "pinecone", "weaviate",
    "qdrant", "milvus", "opensearch", "elasticsearch", "faiss", "chromadb",
    "retrieval", "rag", "semantic search", "ranking", "reranking", "re-ranking",
    "ndcg", "mrr", "a/b test", "evaluation framework", "information retrieval",
    "python", "nlp", "natural language processing", "llm", "large language model",
    "transformers", "bert", "recommendation system", "search system"
]

JD_BONUS_SKILLS = [
    "lora", "qlora", "peft", "fine-tuning", "fine tuning", "finetuning",
    "learning to rank", "xgboost", "bm25", "hr tech", "recruiting tech",
    "distributed systems", "inference optimization", "open source",
    "bgge", "e5", "openai", "langchain", "huggingface", "pytorch", "tensorflow"
]

# Disqualifying signals from JD
CONSULTING_COMPANIES = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "tech mahindra", "mphasis", "hexaware", "mindtree", "ltimindtree",
    "l&t infotech", "niit technologies", "kpit", "persistent systems"
}

CV_DOMAIN_ONLY = ["computer vision", "speech recognition", "robotics", "autonomous driving"]
PREFERRED_LOCATIONS = {
    "noida", "pune", "delhi", "gurgaon", "bangalore", "hyderabad", "mumbai",
    "new delhi", "bengaluru", "gurugram"
}
PRODUCT_COMPANIES_SIGNALS = [
    "startup", "series a", "series b", "series c", "saas", "product", "platform"
]

REFERENCE_DATE = datetime(2026, 6, 4)


# ─── FEATURE EXTRACTION ──────────────────────────────────────────────────────

def build_candidate_text(c: dict) -> str:
    """Build a rich text blob for TF-IDF from all relevant fields."""
    parts = []
    p = c.get("profile", {})
    parts.append(p.get("headline", ""))
    parts.append(p.get("summary", ""))
    parts.append(p.get("current_title", ""))
    parts.append(p.get("current_industry", ""))

    for job in c.get("career_history", []):
        parts.append(job.get("title", ""))
        parts.append(job.get("description", ""))
        parts.append(job.get("industry", ""))

    for skill in c.get("skills", []):
        parts.append(skill.get("name", ""))

    for cert in c.get("certifications", []):
        parts.append(cert.get("name", ""))
        parts.append(cert.get("issuer", ""))

    return " ".join(parts).lower()


def skills_score(c: dict) -> tuple[float, int, int]:
    """Score candidate on required/bonus skills. Returns (score, req_hits, bonus_hits)."""
    # Collect all skill names + career text for matching
    skill_names = {s["name"].lower() for s in c.get("skills", [])}
    all_text = build_candidate_text(c)

    req_hits = 0
    for skill in JD_REQUIRED_SKILLS:
        if skill in all_text or skill in skill_names:
            req_hits += 1

    bonus_hits = 0
    for skill in JD_BONUS_SKILLS:
        if skill in all_text or skill in skill_names:
            bonus_hits += 1

    req_score = min(1.0, req_hits / 8)  # cap at 8 required hits = full score
    bonus_score = min(0.3, bonus_hits * 0.05)
    return req_score + bonus_score, req_hits, bonus_hits


def career_quality_score(c: dict) -> tuple[float, dict]:
    """Score career trajectory for product co. experience, title fit, tenure."""
    p = c.get("profile", {})
    history = c.get("career_history", [])
    signals = {}

    yoe = p.get("years_of_experience", 0)
    # Ideal: 5-9 years, slightly penalize <4 or >12
    if 5 <= yoe <= 9:
        yoe_score = 1.0
    elif 4 <= yoe < 5 or 9 < yoe <= 11:
        yoe_score = 0.8
    elif 3 <= yoe < 4 or 11 < yoe <= 13:
        yoe_score = 0.5
    else:
        yoe_score = 0.2
    signals["yoe_score"] = yoe_score

    # Title fit
    title = p.get("current_title", "").lower()
    title_score = 0.0
    if any(x in title for x in ["senior ai", "staff ai", "principal ai", "lead ai"]):
        title_score = 1.0
    elif any(x in title for x in ["ml engineer", "machine learning engineer", "ai engineer"]):
        title_score = 0.95
    elif any(x in title for x in ["senior ml", "senior software engineer (ml)", "applied scientist"]):
        title_score = 0.85
    elif any(x in title for x in ["ai specialist", "ai research engineer"]):
        title_score = 0.75
    elif any(x in title for x in ["data scientist", "nlp engineer", "research engineer"]):
        title_score = 0.65
    elif any(x in title for x in ["software engineer", "backend engineer", "full stack"]):
        title_score = 0.35
    elif any(x in title for x in ["manager", "director", "vp", "head of"]):
        title_score = 0.1  # moved too far from IC
    signals["title_score"] = title_score

    # Product company vs. services
    product_co_months = 0
    services_only = True
    total_months = 0
    for job in history:
        co = job.get("company", "").lower()
        dur = job.get("duration_months", 0) or 0
        total_months += dur
        is_consulting = any(c_name in co for c_name in CONSULTING_COMPANIES)
        if not is_consulting:
            services_only = False
            product_co_months += dur

    product_ratio = product_co_months / max(total_months, 1)
    product_score = product_ratio
    signals["product_ratio"] = product_ratio
    signals["services_only"] = services_only

    # Tenure stability (avoid job hoppers)
    if len(history) >= 2:
        avg_tenure = total_months / len(history)
        if avg_tenure >= 24:
            tenure_score = 1.0
        elif avg_tenure >= 18:
            tenure_score = 0.8
        elif avg_tenure >= 12:
            tenure_score = 0.6
        else:
            tenure_score = 0.3
    else:
        tenure_score = 0.7
    signals["tenure_score"] = tenure_score

    # Research-only penalty (pure academic/research labs without production)
    research_only = False
    all_titles = [j.get("title", "").lower() for j in history]
    all_industries = [j.get("industry", "").lower() for j in history]
    if all(any(x in t for x in ["research", "intern", "phd", "postdoc"]) for t in all_titles):
        research_only = True
    signals["research_only"] = research_only

    score = 0.3 * yoe_score + 0.3 * title_score + 0.25 * product_score + 0.15 * tenure_score
    if services_only:
        score *= 0.5
    if research_only:
        score *= 0.4

    return score, signals


def behavioral_score(c: dict) -> tuple[float, dict]:
    """Score platform engagement signals."""
    s = c.get("redrob_signals", {})
    signals = {}

    # Recency: days since last active
    last_active = s.get("last_active_date")
    if last_active:
        try:
            la_date = datetime.strptime(last_active, "%Y-%m-%d")
            days_inactive = (REFERENCE_DATE - la_date).days
            if days_inactive <= 7:
                recency = 1.0
            elif days_inactive <= 30:
                recency = 0.85
            elif days_inactive <= 90:
                recency = 0.6
            elif days_inactive <= 180:
                recency = 0.3
            else:
                recency = 0.05
        except:
            recency = 0.5
    else:
        recency = 0.5
    signals["recency"] = recency
    signals["days_inactive"] = days_inactive if last_active else 999

    # Open to work
    open_to_work = 1.0 if s.get("open_to_work_flag", False) else 0.4
    signals["open_to_work"] = open_to_work

    # Recruiter response rate
    response_rate = s.get("recruiter_response_rate", 0.5)
    rr_score = min(1.0, response_rate * 1.2)  # boost good responders
    signals["response_rate"] = response_rate

    # Notice period (prefer < 30 days)
    notice = s.get("notice_period_days", 60)
    if notice <= 15:
        notice_score = 1.0
    elif notice <= 30:
        notice_score = 0.85
    elif notice <= 60:
        notice_score = 0.6
    elif notice <= 90:
        notice_score = 0.35
    else:
        notice_score = 0.1
    signals["notice_days"] = notice

    # Profile completeness
    completeness = s.get("profile_completeness_score", 50) / 100.0

    # Interview completion rate (reliability signal)
    icr = s.get("interview_completion_rate", 0.5)
    icr_score = icr

    # GitHub activity (bonus for active open-source contributors)
    github = s.get("github_activity_score", -1)
    if github == -1:
        github_score = 0.4  # neutral
    else:
        github_score = min(1.0, github / 70.0)
    signals["github_score"] = github_score

    # Saved by recruiters (social proof)
    saved = min(1.0, s.get("saved_by_recruiters_30d", 0) / 10.0)

    score = (
        0.25 * recency +
        0.20 * rr_score +
        0.15 * open_to_work +
        0.15 * notice_score +
        0.10 * completeness +
        0.08 * icr_score +
        0.07 * github_score
    )
    return score, signals


def location_score(c: dict) -> float:
    """Score location fit."""
    p = c.get("profile", {})
    loc = (p.get("location", "") + " " + p.get("country", "")).lower()
    sig = c.get("redrob_signals", {})
    relocate = sig.get("willing_to_relocate", False)

    # Preferred India cities
    if any(city in loc for city in PREFERRED_LOCATIONS):
        return 1.0
    # India generally
    if "india" in loc or any(state in loc for state in [
        "maharashtra", "karnataka", "telangana", "delhi", "haryana",
        "uttar pradesh", "tamil nadu", "gujarat", "rajasthan"
    ]):
        return 0.8
    # Willing to relocate from anywhere
    if relocate:
        return 0.6
    # Outside India, not willing to relocate
    return 0.2


def disqualifier_flags(c: dict) -> tuple[float, list]:
    """Return a multiplier (0–1) and list of flag reasons."""
    flags = []
    multiplier = 1.0
    p = c.get("profile", {})
    history = c.get("career_history", [])
    title = p.get("current_title", "").lower()
    skills_text = " ".join(s["name"].lower() for s in c.get("skills", []))
    all_text = build_candidate_text(c)

    # Consulting-only career
    all_companies = [j.get("company", "").lower() for j in history]
    if all(any(c_name in co for c_name in CONSULTING_COMPANIES) for co in all_companies) and len(all_companies) > 1:
        multiplier *= 0.3
        flags.append("consulting_only_career")

    # Clearly wrong role (non-tech roles)
    if any(x in title for x in ["marketing", "accountant", "sales", "hr manager", "finance",
                                  "operations manager", "civil engineer", "mechanical",
                                  "customer support", "content writer"]):
        multiplier *= 0.05
        flags.append("wrong_role_title")

    # CV/Speech/Robotics only domain
    if any(x in all_text for x in CV_DOMAIN_ONLY):
        # Only penalize if these dominate without NLP/IR
        if not any(x in all_text for x in ["nlp", "retrieval", "ranking", "embedding", "search"]):
            multiplier *= 0.4
            flags.append("cv_speech_domain_only")

    # Title chaser pattern (many short stints)
    if len(history) >= 3:
        short_stints = sum(1 for j in history if (j.get("duration_months") or 0) < 14)
        if short_stints >= len(history) - 1:
            multiplier *= 0.7
            flags.append("job_hopper")

    # Honeypot detection: impossible timelines
    for job in history:
        dur = job.get("duration_months", 0) or 0
        start = job.get("start_date", "")
        company = job.get("company", "")
        # Check if skills list has 10+ "expert" level skills with suspiciously low durations
    expert_skills = [s for s in c.get("skills", []) if s.get("proficiency") == "expert"]
    if len(expert_skills) >= 8:
        # Expert in 8+ skills is suspicious
        multiplier *= 0.5
        flags.append("suspicious_expert_count")

    # Pure LangChain/framework tutorial pattern (no substance)
    framework_buzz = sum(1 for x in ["langchain", "llamaindex", "langflow"] if x in all_text)
    substance = sum(1 for x in ["production", "deployed", "scale", "millions", "latency",
                                  "ndcg", "mrr", "evaluation", "a/b", "embedding drift"] if x in all_text)
    if framework_buzz >= 2 and substance == 0:
        multiplier *= 0.6
        flags.append("framework_enthusiast_no_substance")

    # Recent LLM wrapper only (no pre-LLM experience)
    yoe = p.get("years_of_experience", 0)
    if yoe < 2:
        multiplier *= 0.4
        flags.append("too_junior")

    return multiplier, flags


def honeypot_detection(c: dict) -> bool:
    """Detect clearly impossible/fabricated profiles."""
    history = c.get("career_history", [])
    p = c.get("profile", {})
    yoe = p.get("years_of_experience", 0)

    # Check for timeline impossibilities
    total_months_claimed = sum(j.get("duration_months", 0) or 0 for j in history)
    if total_months_claimed > yoe * 12 * 1.3:  # 30% slack
        return True

    # Too many expert skills with zero endorsements collectively
    expert_skills = [s for s in c.get("skills", []) if s.get("proficiency") == "expert"]
    if len(expert_skills) >= 10:
        total_endorsements = sum(s.get("endorsements", 0) for s in expert_skills)
        if total_endorsements < 5:
            return True

    # YoE of 8+ at company that seems fictional/small (can't verify but look for patterns)
    # Profile completeness 100 with 0 skill assessment scores
    sig = c.get("redrob_signals", {})
    if sig.get("profile_completeness_score", 0) >= 99:
        assessments = sig.get("skill_assessment_scores", {})
        if assessments and all(v == 0 for v in assessments.values()):
            return True

    return False


# ─── MAIN RANKING PIPELINE ───────────────────────────────────────────────────

def load_candidates(path: str) -> list[dict]:
    candidates = []
    skipped = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                candidates.append(json.loads(line))
            except json.JSONDecodeError as e:
                skipped += 1
                print(f"  Skipping line {i} (bad JSON): {e}")
    if skipped:
        print(f"  Warning: skipped {skipped} malformed lines out of {i} total.")
    return candidates


def build_tfidf_scores(candidates: list[dict]) -> np.ndarray:
    """Compute TF-IDF cosine similarity of each candidate vs JD."""
    print(f"  Building TF-IDF on {len(candidates)} candidates...")
    texts = [build_candidate_text(c) for c in candidates]
    texts.append(JD_TEXT.lower())  # JD as last doc

    vectorizer = TfidfVectorizer(
        max_features=15000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
        max_df=0.95,
        stop_words='english'
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    jd_vec = tfidf_matrix[-1]
    candidate_vecs = tfidf_matrix[:-1]

    sims = cosine_similarity(candidate_vecs, jd_vec).flatten()
    return sims


def generate_reasoning(c: dict, rank: int, score: float, feat: dict) -> str:
    """Generate specific, honest per-candidate reasoning."""
    p = c.get("profile", {})
    sig = c.get("redrob_signals", {})
    title = p.get("current_title", "Unknown")
    yoe = p.get("years_of_experience", 0)
    loc = p.get("location", "Unknown")
    company = p.get("current_company", "Unknown")
    rr = sig.get("recruiter_response_rate", 0)
    notice = sig.get("notice_period_days", 60)
    last_active = sig.get("last_active_date", "unknown")

    flags = feat.get("flags", [])
    req_hits = feat.get("req_hits", 0)
    bonus_hits = feat.get("bonus_hits", 0)
    days_inactive = feat.get("days_inactive", 999)

    # Positives
    pos_parts = []
    if req_hits >= 6:
        pos_parts.append(f"strong core skills match ({req_hits}/{len(JD_REQUIRED_SKILLS)} required signals)")
    elif req_hits >= 3:
        pos_parts.append(f"moderate skills match ({req_hits} required signals)")

    if bonus_hits >= 3:
        pos_parts.append(f"{bonus_hits} bonus signals (fine-tuning, LTR, etc.)")

    if yoe >= 5 and yoe <= 9:
        pos_parts.append(f"{yoe:.1f} yrs experience in target range")

    career_s = feat.get("career_signals", {})
    if career_s.get("product_ratio", 0) > 0.6:
        pos_parts.append("primarily product-company background")

    if rr >= 0.7:
        pos_parts.append(f"high recruiter response rate ({rr:.0%})")
    
    if days_inactive <= 14:
        pos_parts.append("recently active on platform")

    if notice <= 30:
        pos_parts.append(f"short notice ({notice}d)")

    if sig.get("open_to_work_flag"):
        pos_parts.append("open to work")

    # Concerns
    concern_parts = []
    if "consulting_only_career" in flags:
        concern_parts.append("consulting-only career trajectory")
    if "wrong_role_title" in flags:
        concern_parts.append(f"title mismatch ({title})")
    if "job_hopper" in flags:
        concern_parts.append("short average tenure across roles")
    if days_inactive > 90:
        concern_parts.append(f"inactive {days_inactive}d — availability uncertain")
    if rr < 0.3:
        concern_parts.append(f"low response rate ({rr:.0%})")
    if notice > 90:
        concern_parts.append(f"long notice period ({notice}d)")
    if yoe < 4:
        concern_parts.append(f"only {yoe:.1f} yrs experience (below JD minimum)")
    if yoe > 12:
        concern_parts.append(f"{yoe:.1f} yrs — verify still writes code (not pure architect)")
    if career_s.get("services_only"):
        concern_parts.append("services-company career only")

    # Build sentence
    if pos_parts and concern_parts:
        reasoning = f"{title} @ {company}, {yoe:.1f}yrs, {loc}. Strengths: {'; '.join(pos_parts[:2])}. Concerns: {'; '.join(concern_parts[:2])}."
    elif pos_parts:
        reasoning = f"{title} @ {company}, {yoe:.1f}yrs, {loc}. {'; '.join(pos_parts[:3])}."
    else:
        if concern_parts:
            reasoning = f"{title} @ {company}, {yoe:.1f}yrs, {loc}. Ranked for completeness; concerns: {'; '.join(concern_parts[:2])}."
        else:
            reasoning = f"{title} @ {company}, {yoe:.1f}yrs, {loc}. Included in tail of shortlist; borderline fit on skills and signals."

    return reasoning[:300]  # cap length


def rank_candidates(candidates_path: str, output_path: str):
    print("Loading candidates...")
    candidates = load_candidates(candidates_path)
    n = len(candidates)
    print(f"Loaded {n} candidates.")

    print("Computing TF-IDF semantic scores...")
    tfidf_scores = build_tfidf_scores(candidates)

    # Normalize TF-IDF to 0-1
    tmax = tfidf_scores.max()
    tmin = tfidf_scores.min()
    tfidf_norm = (tfidf_scores - tmin) / (tmax - tmin + 1e-9)

    print("Computing structured feature scores...")
    rows = []
    for i, c in enumerate(candidates):
        cid = c["candidate_id"]

        # Honeypot check
        if honeypot_detection(c):
            rows.append({
                "candidate_id": cid,
                "score": 0.001,
                "features": {"honeypot": True, "flags": ["honeypot"], "req_hits": 0, "bonus_hits": 0,
                              "career_signals": {}, "days_inactive": 999}
            })
            continue

        sk_score, req_hits, bonus_hits = skills_score(c)
        cq_score, career_signals = career_quality_score(c)
        beh_score, beh_signals = behavioral_score(c)
        loc_score_val = location_score(c)
        disq_mult, flags = disqualifier_flags(c)

        semantic = tfidf_norm[i]

        # Weighted composite (before disqualifier)
        raw_score = (
            0.28 * semantic +       # semantic relevance
            0.28 * sk_score +       # skills match
            0.20 * cq_score +       # career quality
            0.14 * beh_score +      # behavioral engagement
            0.10 * loc_score_val    # location fit
        )

        final_score = raw_score * disq_mult

        rows.append({
            "candidate_id": cid,
            "score": final_score,
            "features": {
                "semantic": semantic,
                "skills_score": sk_score,
                "career_score": cq_score,
                "behavioral_score": beh_score,
                "location_score": loc_score_val,
                "disq_multiplier": disq_mult,
                "flags": flags,
                "req_hits": req_hits,
                "bonus_hits": bonus_hits,
                "career_signals": career_signals,
                "days_inactive": beh_signals.get("days_inactive", 999),
            }
        })

    print("Sorting and selecting top 100...")
    rows.sort(key=lambda x: x["score"], reverse=True)
    top100 = rows[:100]

    # Write output
    print(f"Writing submission to {output_path}...")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank_idx, row in enumerate(top100, start=1):
            cid = row["candidate_id"]
            score = round(row["score"], 6)
            feat = row["features"]

            # Find original candidate object
            c_obj = next(c for c in candidates if c["candidate_id"] == cid)
            reasoning = generate_reasoning(c_obj, rank_idx, score, feat)

            writer.writerow([cid, rank_idx, score, reasoning])

    print(f"\nDone! Top 5 candidates:")
    for r in top100[:5]:
        cid = r["candidate_id"]
        c_obj = next(c for c in candidates if c["candidate_id"] == cid)
        print(f"  {cid} | score={r['score']:.4f} | {c_obj['profile']['current_title']} | {c_obj['profile']['years_of_experience']}yrs | {c_obj['profile']['location']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranker")
    parser.add_argument("--candidates", default="candidates.jsonl", help="Path to candidates.jsonl")
    parser.add_argument("--out", default="submission.csv", help="Output CSV path")
    args = parser.parse_args()
    rank_candidates(args.candidates, args.out)
