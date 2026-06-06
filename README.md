# Redrob Hackathon — Intelligent Candidate Ranking System

**Team:** team_001  
**Challenge:** India Runs Data & AI Challenge — Intelligent Candidate Discovery & Ranking  
**Stack:** Python 3.11+, scikit-learn, numpy, pandas (CPU-only, no GPU, no external APIs)

---

## Architecture Overview

A **multi-signal hybrid scorer** that ranks candidates the way a great recruiter would — not keyword matching, but structured reasoning about fit.

### Scoring Pipeline (5 components)

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| Semantic Relevance | 28% | TF-IDF cosine similarity of full candidate text vs JD (bigrams, 15K features) |
| Skills Match | 28% | Hard-required skills + bonus skills with partial credit |
| Career Quality | 20% | Product co. ratio, title fit, YoE band, tenure stability |
| Behavioral Signals | 14% | Recency, response rate, open-to-work, notice period, GitHub |
| Location Fit | 10% | Preferred cities → India → relocation willing → abroad |

On top of the weighted score, **disqualifier multipliers** are applied:
- Consulting-only career → ×0.30
- Wrong role title (marketing, accountant, etc.) → ×0.05
- Job-hopper pattern → ×0.70
- CV/speech domain only, no NLP/IR → ×0.40
- Honeypot profiles (impossible timelines, 10+ expert skills, zero endorsements) → score capped near 0

---

## Quickstart

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the ranker
```bash
python src/rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

Runtime: ~55 seconds on a CPU-only machine with 16 GB RAM (100K candidates).

### 3. Validate output
```bash
python scripts/validate_submission.py submission.csv
```

---

## Project Structure

```
.
├── src/
│   └── rank.py                  # Main ranking system (single entrypoint)
├── scripts/
│   └── validate_submission.py   # Official format validator
├── docs/
│   └── approach_deck.pdf        # Methodology presentation
├── submission.csv               # Final ranked output (top 100)
├── submission_metadata.yaml     # Team metadata
├── requirements.txt
└── README.md
```

---

## Key Design Decisions

### Why TF-IDF over dense embeddings?
The compute constraint (5 min CPU, 16 GB RAM, no GPU) rules out running sentence-transformers over 100K candidates in the ranking step. TF-IDF with bigrams over 15K features gives strong semantic overlap at milliseconds per candidate. Dense embeddings would be pre-computed in a production system but require disk artifacts.

### Why not pure LLM scoring?
Per submission spec Section 3: no external API calls during ranking. A local LLM per-candidate would easily exceed the 5-minute wall-clock budget. Our approach: LLM-quality reasoning from structured signals, LLM-speed from vectorized operations.

### Disqualifiers before score aggregation
The JD explicitly states disqualifying patterns. We apply multiplicative penalties rather than additive penalties so a great score in one dimension cannot "rescue" a truly disqualifying factor.

### Honeypot detection
We check for: timeline impossibilities (claimed months > YoE × 12 × 1.3), implausibly many "expert" skills with zero endorsements, and perfect completeness with all-zero assessment scores. These profiles are scored near 0.

---

## Behavioral Signal Weighting

| Signal | Sub-weight | Rationale |
|--------|-----------|-----------|
| Recency (days since login) | 25% | Stale profiles = unavailable |
| Recruiter response rate | 20% | Hirable only if reachable |
| Open to work flag | 15% | Explicit availability signal |
| Notice period | 15% | JD prefers sub-30 days |
| Profile completeness | 10% | Engagement proxy |
| Interview completion rate | 8% | Reliability signal |
| GitHub activity | 7% | Open source = external validation |

---

## Reproducing the Submission

The submitted `submission.csv` was generated with:
```bash
python src/rank.py \
  --candidates ./candidates.jsonl \
  --out ./submission.csv
```

Environment: Python 3.12, scikit-learn 1.8.0, numpy 2.4.4, pandas 3.0.2  
Runtime: ~55 seconds wall-clock | Peak RAM: ~3.5 GB | No GPU | No network calls

---

## AI Tools Declaration
Claude (Anthropic) was used as a development assistant. All architecture decisions, scoring logic, and code were authored and validated by the team.
