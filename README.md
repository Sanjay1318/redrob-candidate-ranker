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

### 1. Clone the repo
```bash
git clone https://github.com/Sanjay1318/redrob-candidate-ranker.git
cd redrob-candidate-ranker
```

### 2. Download the dataset
> **Note:** `candidates.jsonl` is NOT included in this repo (464 MB).  
> Download it from the official hackathon dataset link and place it in the project root:
> ```
> redrob-candidate-ranker/
> └── candidates.jsonl   ← place here
> ```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the ranker
```bash
python src/rank.py --candidates candidates.jsonl --out submission.csv
```

Runtime: ~55 seconds on CPU with 16 GB RAM (100K candidates).

### 5. Validate output
```bash
python scripts/validate_submission.py submission.csv
```

### 6. Regenerate the PDF deck (optional)
```bash
python scripts/build_deck.py docs/approach_deck.pdf
```

---

## Project Structure

```
redrob-candidate-ranker/
├── src/
│   └── rank.py                   # Main ranking system (single entrypoint)
├── scripts/
│   ├── build_deck.py             # Generates the PDF approach deck
│   └── validate_submission.py    # Official format validator
├── docs/
│   └── approach_deck.pdf         # Methodology presentation (12 slides)
├── submission.csv                # Final ranked output (top 100 candidates)
├── submission_metadata.yaml      # Team metadata
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Key Design Decisions

### Why TF-IDF over dense embeddings?
The compute constraint (5 min CPU, 16 GB RAM, no GPU) rules out running sentence-transformers over 100K candidates in the ranking step. TF-IDF with bigrams over 15K features gives strong semantic overlap at milliseconds per candidate.

### Why not pure LLM scoring?
Per submission spec: no external API calls during ranking. A local LLM per-candidate would exceed the 5-minute wall-clock budget. Our approach delivers LLM-quality reasoning from structured signals at TF-IDF speed.

### Disqualifiers before score aggregation
The JD explicitly states disqualifying patterns. We apply multiplicative penalties so a great score in one dimension cannot rescue a truly disqualifying factor.

### Honeypot detection
We check for: timeline impossibilities (claimed months > YoE × 12 × 1.3), implausibly many "expert" skills with zero endorsements, and perfect completeness with all-zero assessment scores.

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

```bash
python src/rank.py \
  --candidates ./candidates.jsonl \
  --out ./submission.csv
```

Environment: Python 3.12, scikit-learn 1.8.0, numpy 2.4.4, pandas 3.0.2  
Runtime: ~55 seconds | Peak RAM: ~3.5 GB | No GPU | No network calls

---

## AI Tools Declaration
Claude (Anthropic) was used as a development assistant. All architecture decisions, scoring logic, and code were authored and validated by the team.
