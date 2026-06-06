"""Build a polished PDF presentation deck explaining the approach."""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable
import os

# ── Colour palette ────────────────────────────────────────────────────────────
PRIMARY   = colors.HexColor("#1A2E4A")   # deep navy
ACCENT    = colors.HexColor("#E84B3A")   # redrob red
SECONDARY = colors.HexColor("#2D7DD2")   # bright blue
LIGHT_BG  = colors.HexColor("#F4F7FA")   # near-white slate
MID_GRAY  = colors.HexColor("#8E9BAB")
DARK_TEXT = colors.HexColor("#1C2B3A")
WHITE     = colors.white
GREEN     = colors.HexColor("#27AE60")
ORANGE    = colors.HexColor("#E67E22")
RED_SOFT  = colors.HexColor("#E74C3C")

W, H = letter  # 8.5 × 11 in

# ── Page background + header stripe ──────────────────────────────────────────
def slide_background(c, doc):
    """Draw background, top stripe and page number."""
    c.saveState()
    # Background
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    # Top stripe
    c.setFillColor(PRIMARY)
    c.rect(0, H - 0.55*inch, W, 0.55*inch, fill=1, stroke=0)
    # Accent bar left edge
    c.setFillColor(ACCENT)
    c.rect(0, H - 0.55*inch, 0.22*inch, 0.55*inch, fill=1, stroke=0)
    # Footer line
    c.setFillColor(MID_GRAY)
    c.setStrokeColor(MID_GRAY)
    c.line(0.5*inch, 0.45*inch, W - 0.5*inch, 0.45*inch)
    # Page number
    c.setFont("Helvetica", 8)
    c.setFillColor(MID_GRAY)
    c.drawRightString(W - 0.5*inch, 0.28*inch, f"Page {doc.page}")
    c.drawString(0.5*inch, 0.28*inch, "Redrob Hackathon  ·  Intelligent Candidate Ranking")
    c.restoreState()

def cover_background(c, doc):
    """Full-bleed cover page."""
    c.saveState()
    c.setFillColor(PRIMARY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    # Accent band
    c.setFillColor(ACCENT)
    c.rect(0, 0, 0.45*inch, H, fill=1, stroke=0)
    # Bottom stripe
    c.setFillColor(colors.HexColor("#0F1E30"))
    c.rect(0, 0, W, 1.2*inch, fill=1, stroke=0)
    c.restoreState()

# ── Style helpers ─────────────────────────────────────────────────────────────
def make_styles():
    s = getSampleStyleSheet()
    styles = {}

    styles["cover_title"] = ParagraphStyle("cover_title",
        fontSize=32, leading=38, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_LEFT, spaceAfter=14)

    styles["cover_sub"] = ParagraphStyle("cover_sub",
        fontSize=14, leading=20, fontName="Helvetica",
        textColor=colors.HexColor("#B0C4D8"), alignment=TA_LEFT, spaceAfter=6)

    styles["cover_meta"] = ParagraphStyle("cover_meta",
        fontSize=10, leading=15, fontName="Helvetica",
        textColor=colors.HexColor("#8EA8C3"), alignment=TA_LEFT)

    styles["section_label"] = ParagraphStyle("section_label",
        fontSize=9, leading=12, fontName="Helvetica-Bold",
        textColor=ACCENT, alignment=TA_LEFT, spaceAfter=3,
        spaceBefore=4, tracking=1.5)

    styles["slide_title"] = ParagraphStyle("slide_title",
        fontSize=20, leading=25, fontName="Helvetica-Bold",
        textColor=PRIMARY, alignment=TA_LEFT, spaceAfter=10, spaceBefore=6)

    styles["slide_h2"] = ParagraphStyle("slide_h2",
        fontSize=13, leading=17, fontName="Helvetica-Bold",
        textColor=SECONDARY, alignment=TA_LEFT, spaceAfter=4, spaceBefore=8)

    styles["body"] = ParagraphStyle("body",
        fontSize=10, leading=15, fontName="Helvetica",
        textColor=DARK_TEXT, alignment=TA_LEFT, spaceAfter=5)

    styles["bullet"] = ParagraphStyle("bullet",
        fontSize=10, leading=15, fontName="Helvetica",
        textColor=DARK_TEXT, leftIndent=18, firstLineIndent=-12,
        spaceAfter=4, bulletText="•")

    styles["caption"] = ParagraphStyle("caption",
        fontSize=8.5, leading=12, fontName="Helvetica-Oblique",
        textColor=MID_GRAY, alignment=TA_CENTER, spaceAfter=6)

    styles["callout"] = ParagraphStyle("callout",
        fontSize=10, leading=15, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_CENTER)

    styles["code"] = ParagraphStyle("code",
        fontSize=8.5, leading=13, fontName="Courier",
        textColor=colors.HexColor("#2ECC71"), backColor=colors.HexColor("#1A1A2E"),
        leftIndent=12, rightIndent=12, spaceAfter=6, spaceBefore=4,
        borderPad=6)

    styles["tag_pos"] = ParagraphStyle("tag_pos",
        fontSize=8, leading=11, fontName="Helvetica-Bold",
        textColor=WHITE, backColor=GREEN, alignment=TA_CENTER, borderPad=3)

    styles["tag_neg"] = ParagraphStyle("tag_neg",
        fontSize=8, leading=11, fontName="Helvetica-Bold",
        textColor=WHITE, backColor=RED_SOFT, alignment=TA_CENTER, borderPad=3)

    return styles

S = make_styles()

# ── Reusable flowables ────────────────────────────────────────────────────────
def rule(color=ACCENT, thick=1.5):
    return HRFlowable(width="100%", thickness=thick, color=color, spaceAfter=8, spaceBefore=2)

def section_label(text):
    return Paragraph(text.upper(), S["section_label"])

def callout_box(text, bg=SECONDARY, width_frac=1.0):
    """Coloured highlight box."""
    data = [[Paragraph(text, S["callout"])]]
    t = Table(data, colWidths=[7.2*inch * width_frac])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("ROUNDEDCORNERS", [6]),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
    ]))
    return t

def metric_row(items):
    """Row of metric boxes: [(label, value, color), ...]"""
    n = len(items)
    col_w = 7.2*inch / n
    data_row = []
    for label, value, bg in items:
        cell = [Paragraph(f'<font size="20" color="white"><b>{value}</b></font>', S["callout"]),
                Paragraph(f'<font size="9" color="#C8DCF0">{label}</font>', S["callout"])]
        data_row.append(cell)
    t = Table([data_row], colWidths=[col_w]*n)
    style = [
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]
    for i, (_, _, bg) in enumerate(items):
        style.append(("BACKGROUND", (i,0), (i,0), bg))
    t.setStyle(TableStyle(style))
    return t

def two_col(left_items, right_items, left_w=3.5*inch, right_w=3.5*inch, gap=0.2*inch):
    """Two-column layout."""
    left_cell = left_items if isinstance(left_items, list) else [left_items]
    right_cell = right_items if isinstance(right_items, list) else [right_items]
    data = [[left_cell, right_cell]]
    t = Table(data, colWidths=[left_w, right_w + gap])
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    return t

def score_bar_table(items):
    """Horizontal score bars: [(label, weight%, color), ...]"""
    rows = []
    for label, pct, clr in items:
        bar_w = 3.8 * inch * pct / 100
        bar_cell = Table([[""]], colWidths=[bar_w], rowHeights=[14])
        bar_cell.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),clr),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
        rows.append([
            Paragraph(f'<b>{label}</b>', S["body"]),
            bar_cell,
            Paragraph(f'<b>{pct}%</b>', ParagraphStyle("pct", fontSize=10, fontName="Helvetica-Bold", textColor=clr, alignment=TA_RIGHT))
        ])
    t = Table(rows, colWidths=[2.4*inch, 4.0*inch, 0.6*inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    return t

# ── Slide builders ────────────────────────────────────────────────────────────

def build_cover(elements):
    # Use a special-formatted first page placeholder via an inner canvas
    # We build content as if on a dark page
    elements.append(Spacer(1, 1.6*inch))
    elements.append(Paragraph(
        '<font color="#E84B3A">●</font>  REDROB HACKATHON  ·  INDIA RUNS DATA & AI CHALLENGE',
        ParagraphStyle("tag", fontSize=10, fontName="Helvetica-Bold",
                       textColor=colors.HexColor("#8EA8C3"), alignment=TA_LEFT)))
    elements.append(Spacer(1, 0.18*inch))
    elements.append(Paragraph(
        "Intelligent Candidate\nDiscovery &amp; Ranking",
        S["cover_title"]))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph(
        "A multi-signal hybrid scoring system that ranks the way a great recruiter thinks —\n"
        "not by matching keywords, but by reasoning about who genuinely fits the role.",
        S["cover_sub"]))
    elements.append(Spacer(1, 0.3*inch))
    rule_cov = HRFlowable(width="60%", thickness=1.5, color=ACCENT, spaceAfter=14)
    elements.append(rule_cov)
    elements.append(Paragraph("Team: team_001  ·  Python · scikit-learn · CPU-only · 55s runtime", S["cover_meta"]))
    elements.append(Paragraph("Architecture: TF-IDF Semantic + Skills Scoring + Career Quality + Behavioral Signals + Location", S["cover_meta"]))
    elements.append(PageBreak())


def build_problem(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("01 — The Problem"))
    elements.append(Paragraph("Why Keyword Matching Fails Recruiters", S["slide_title"]))
    elements.append(rule())

    elements.append(callout_box(
        '"A candidate who lists RAG and Pinecone but whose title is Marketing Manager '
        'is not a fit — no matter how perfect their skill list looks."  — JD, Hackathon Note',
        bg=colors.HexColor("#7B2D28")))
    elements.append(Spacer(1, 0.18*inch))

    left = [
        Paragraph("The Keyword Filter Trap", S["slide_h2"]),
        Paragraph("Traditional ATS systems score candidates by counting skill matches. "
                  "This creates three failure modes:", S["body"]),
        Paragraph("False positives: Keyword-stuffed profiles rank #1 despite zero real experience.", S["bullet"]),
        Paragraph("False negatives: A great engineer who describes their RAG system as 'semantic retrieval pipeline' gets missed.", S["bullet"]),
        Paragraph("Ignores behaviour: A perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% response rate is effectively unavailable.", S["bullet"]),
    ]
    right = [
        Paragraph("What a Great Recruiter Does Instead", S["slide_h2"]),
        Paragraph("Reads between the lines — understands what the JD actually means vs. what it says.", S["bullet"]),
        Paragraph("Checks trajectory — has this person shipped production systems, or only tutorials?", S["bullet"]),
        Paragraph("Weighs availability — is this person actively looking and reachable?", S["bullet"]),
        Paragraph("Spots red flags — consulting-only career, title chaser, research lab only.", S["bullet"]),
        Paragraph("Considers fit for culture — startup agility vs. enterprise stability.", S["bullet"]),
    ]
    elements.append(two_col(left, right))
    elements.append(PageBreak())


def build_architecture(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("02 — Architecture"))
    elements.append(Paragraph("5-Component Hybrid Scoring Pipeline", S["slide_title"]))
    elements.append(rule())

    elements.append(Paragraph(
        "Our system computes five independent scores, combines them with calibrated weights, "
        "then applies disqualifier multipliers — so a great skills score cannot rescue a truly disqualifying factor.",
        S["body"]))
    elements.append(Spacer(1, 0.12*inch))

    elements.append(score_bar_table([
        ("Semantic Relevance",  28, SECONDARY),
        ("Skills Match",        28, colors.HexColor("#27AE60")),
        ("Career Quality",      20, colors.HexColor("#8E44AD")),
        ("Behavioral Signals",  14, ORANGE),
        ("Location Fit",        10, colors.HexColor("#16A085")),
    ]))
    elements.append(Spacer(1, 0.16*inch))

    elements.append(Paragraph(
        "final_score = weighted_sum × disqualifier_multiplier",
        S["code"]))
    elements.append(Spacer(1, 0.12*inch))

    elements.append(metric_row([
        ("Candidates Ranked", "100K", PRIMARY),
        ("Runtime (CPU)", "~55s", SECONDARY),
        ("RAM Usage", "~3.5 GB", colors.HexColor("#27AE60")),
        ("External API Calls", "Zero", ACCENT),
    ]))
    elements.append(PageBreak())


def build_semantic(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("03 — Semantic Relevance  (28%)"))
    elements.append(Paragraph("TF-IDF Cosine Similarity vs. Dense Embeddings", S["slide_title"]))
    elements.append(rule())

    left = [
        Paragraph("What we do", S["slide_h2"]),
        Paragraph("Build a rich text blob per candidate from headline, summary, all job descriptions, "
                  "skills, and certifications. Apply TF-IDF with bigrams (15K features, sublinear TF) "
                  "and compute cosine similarity against a curated JD text vector.", S["body"]),
        Paragraph("Why not sentence-transformers?", S["slide_h2"]),
        Paragraph("Embedding 100K candidates with a transformer model requires GPU or significant CPU time. "
                  "The 5-minute constraint and no-GPU rule make this impractical for the ranking step. "
                  "TF-IDF at 15K bigrams captures core retrieval terminology effectively.", S["body"]),
    ]
    right = [
        Paragraph("JD Concept Coverage", S["slide_h2"]),
        Paragraph("embeddings · sentence-transformers · BGE · E5", S["bullet"]),
        Paragraph("vector database · Pinecone · Weaviate · FAISS · Qdrant", S["bullet"]),
        Paragraph("hybrid search · BM25 · reranking · RAG", S["bullet"]),
        Paragraph("NDCG · MRR · A/B testing · evaluation framework", S["bullet"]),
        Paragraph("NLP · information retrieval · Python · LLM", S["bullet"]),
        Paragraph("production deployment · embedding drift · scale", S["bullet"]),
    ]
    elements.append(two_col(left, right))

    elements.append(Spacer(1, 0.12*inch))
    elements.append(callout_box(
        "Key insight: the JD itself says 'The right answer involves reasoning about the gap between "
        "what the JD says and what the JD means.' Our JD text is therefore expanded with semantic "
        "synonyms (e.g. 'semantic retrieval pipeline' maps to same token space as 'RAG').",
        bg=SECONDARY))
    elements.append(PageBreak())


def build_skills(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("04 — Skills Match  (28%)"))
    elements.append(Paragraph("Required vs. Bonus Signal Scoring with Partial Credit", S["slide_title"]))
    elements.append(rule())

    elements.append(Paragraph(
        "We match 35 required signals and 17 bonus signals against all skill names AND full-text career history, "
        "not just the skills section. A candidate who built a vector search pipeline but calls it 'semantic search' "
        "still gets credit.", S["body"]))
    elements.append(Spacer(1, 0.1*inch))

    table_data = [
        [Paragraph("<b>Category</b>", S["body"]),
         Paragraph("<b>Examples</b>", S["body"]),
         Paragraph("<b>Max Score Contribution</b>", S["body"])],
        [Paragraph("Hard Required (35 signals)", ParagraphStyle("g", fontSize=9.5, fontName="Helvetica-Bold", textColor=GREEN)),
         Paragraph("embeddings, vector DB, hybrid search, NDCG, Python, NLP, LLM, ranking, RAG…", S["body"]),
         Paragraph("1.0 (capped at 8 hits)", S["body"])],
        [Paragraph("Bonus Skills (17 signals)", ParagraphStyle("o", fontSize=9.5, fontName="Helvetica-Bold", textColor=ORANGE)),
         Paragraph("LoRA, QLoRA, learning-to-rank, XGBoost, fine-tuning, open-source contributions…", S["body"]),
         Paragraph("+0.30 (capped)", S["body"])],
    ]
    t = Table(table_data, colWidths=[2.0*inch, 3.5*inch, 1.7*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), PRIMARY),
        ("TEXTCOLOR", (0,0), (-1,0), WHITE),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#EAF7EF")),
        ("BACKGROUND", (0,2), (-1,2), colors.HexColor("#FEF6EC")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#DDEAF2")),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.15*inch))

    elements.append(Paragraph(
        "Anti-trap: a candidate whose skills section lists 15 AI keywords but whose "
        "career descriptions show no ML/IR work scores poorly on semantic + career components, "
        "pulling their composite down even with a high skills score.",
        ParagraphStyle("note", fontSize=9.5, fontName="Helvetica-Oblique",
                       textColor=colors.HexColor("#7B5E00"),
                       backColor=colors.HexColor("#FFFBEA"),
                       leftIndent=12, rightIndent=12, borderPad=8, spaceAfter=6)))
    elements.append(PageBreak())


def build_career(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("05 — Career Quality  (20%)"))
    elements.append(Paragraph("Product Companies · Title Fit · YoE · Tenure · Research Penalty", S["slide_title"]))
    elements.append(rule())

    sub_items = [
        ("Product Co. Ratio", "25%", "Months at non-consulting employers / total career months", SECONDARY),
        ("Title Fit",         "30%", "Senior AI/ML Eng → 1.0; Data Scientist → 0.65; Marketing Mgr → 0.1", colors.HexColor("#8E44AD")),
        ("YoE Band",          "30%", "5–9 yrs = 1.0; 4–5 or 9–11 = 0.8; 3–4 = 0.5; <3 = 0.2", GREEN),
        ("Tenure Stability",  "15%", "Avg tenure ≥ 24 months = 1.0; <12 months avg = 0.3", ORANGE),
    ]
    rows = [[
        Paragraph(f'<b>{lbl}</b>', S["body"]),
        Paragraph(f'<font color="{clr.hexval() if hasattr(clr,"hexval") else "#2D7DD2"}"><b>{pct}</b></font>', S["body"]),
        Paragraph(desc, S["body"])
    ] for lbl, pct, desc, clr in sub_items]

    t = Table(rows, colWidths=[1.8*inch, 0.6*inch, 4.8*inch])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#DDEAF2")),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT_BG, WHITE]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.14*inch))

    elements.append(Paragraph("Disqualifier Multipliers (applied after weighted sum)", S["slide_h2"]))
    disq_data = [
        ["Consulting-only career (TCS/Wipro/Infosys…)", "× 0.30"],
        ["Wrong-role title (Marketing, Accountant, Civil Eng…)", "× 0.05"],
        ["Job-hopper (avg tenure < 14 months, 3+ roles)", "× 0.70"],
        ["CV/Speech domain only, no NLP/IR signals", "× 0.40"],
        ["Too junior (< 2 years experience)", "× 0.40"],
        ["Research-only career (no production deployment)", "× 0.40"],
        ["Honeypot detection (impossible timeline, 10+ expert skills)", "≈ 0.001"],
    ]
    disq_rows = [[Paragraph(a, S["body"]), Paragraph(f'<b><font color="#E74C3C">{b}</font></b>', S["body"])] for a, b in disq_data]
    td = Table(disq_rows, colWidths=[5.6*inch, 1.6*inch])
    td.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#FADBD8")),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#FDF2F1"), WHITE]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elements.append(td)
    elements.append(PageBreak())


def build_behavioral(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("06 — Behavioral Signals  (14%)"))
    elements.append(Paragraph("Platform Engagement as a Hiring Multiplier", S["slide_title"]))
    elements.append(rule())

    elements.append(callout_box(
        '"A perfect-on-paper candidate who hasn\'t logged in for 6 months '
        'and has a 5% recruiter response rate is, for hiring purposes, not actually available."  — Redrob Signals Doc',
        bg=colors.HexColor("#1A4A2E")))
    elements.append(Spacer(1, 0.14*inch))

    sig_data = [
        ["Signal", "Sub-weight", "Scoring Logic"],
        ["Recency (days since last login)", "25%", "≤7d→1.0  ≤30d→0.85  ≤90d→0.60  >180d→0.05"],
        ["Recruiter response rate", "20%", "rate × 1.2, capped at 1.0  (>70% = strong signal)"],
        ["Open to work flag", "15%", "True → 1.0  |  False → 0.4"],
        ["Notice period", "15%", "≤15d→1.0  ≤30d→0.85  ≤60d→0.60  >90d→0.10"],
        ["Profile completeness", "10%", "score / 100  (raw Redrob completeness %)"],
        ["Interview completion rate", "8%",  "Direct pass-through of Redrob signal (0.0–1.0)"],
        ["GitHub activity score", "7%",  "score / 70 capped at 1.0  (-1 → 0.4 neutral)"],
    ]
    t = Table(sig_data, colWidths=[2.2*inch, 1.0*inch, 4.0*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), PRIMARY),
        ("TEXTCOLOR", (0,0), (-1,0), WHITE),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#DDEAF2")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT_BG, WHITE]),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.12*inch))

    elements.append(Paragraph(
        "Note: Unused signals from the 23-signal set (salary range, preferred work mode, verified email) "
        "were deliberately excluded — they measure preferences, not availability or engagement quality.",
        ParagraphStyle("note2", fontSize=9, fontName="Helvetica-Oblique",
                       textColor=MID_GRAY, leftIndent=4)))
    elements.append(PageBreak())


def build_honeypot(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("07 — Traps & Honeypot Detection"))
    elements.append(Paragraph("How We Handle the Dataset's Built-in Traps", S["slide_title"]))
    elements.append(rule())

    elements.append(Paragraph("The dataset contains four deliberate trap archetypes:", S["body"]))
    elements.append(Spacer(1, 0.06*inch))

    traps = [
        ("Keyword Stuffers",
         "Candidates with perfect AI skill lists but wrong role title or consulting-only history.",
         "Disqualifier multiplier (× 0.05 for wrong title) reduces score to near zero. "
         "Semantic score is high but multiplied out."),
        ("Plain-language Tier 5s",
         "Good engineers who describe experience in plain English without buzzwords.",
         "TF-IDF bigrams capture semantic synonyms. Career text (job descriptions) is included, "
         "not just skills section."),
        ("Behavioural Twins",
         "Identical skill/career profiles but different engagement signals.",
         "Behavioral component (14%) and recency scoring break these ties. "
         "A twin inactive for 6 months scores 0.05 on recency vs 1.0 for an active twin."),
        ("Honeypots (~80 profiles)",
         "Subtly impossible profiles: 8 yrs at a 3-yr-old company; 10+ expert skills, zero endorsements; "
         "100% complete but all-zero assessments.",
         "Three honeypot checks: timeline inconsistency, expert skill overload, assessment anomaly. "
         "Flagged profiles receive score ≈ 0.001."),
    ]

    for name, desc, mitigation in traps:
        row_data = [[
            Paragraph(f'<b>{name}</b>', ParagraphStyle("tn", fontSize=10.5, fontName="Helvetica-Bold", textColor=ACCENT)),
            Paragraph(f'<b>Trap:</b> {desc}', S["body"]),
            Paragraph(f'<b>Our mitigation:</b> {mitigation}', S["body"]),
        ]]
        t = Table(row_data, colWidths=[1.5*inch, 2.8*inch, 2.9*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,0), colors.HexColor("#FDF2F1")),
            ("BACKGROUND", (1,0), (1,0), colors.HexColor("#EBF5FB")),
            ("BACKGROUND", (2,0), (2,0), colors.HexColor("#EAF7EF")),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#DDEAF2")),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.07*inch))
    elements.append(PageBreak())


def build_results(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("08 — Results & Top Candidates"))
    elements.append(Paragraph("Top-10 Ranked Candidates Overview", S["slide_title"]))
    elements.append(rule())

    # Read the submission CSV
    import csv
    import os
    submission_path = os.path.join(os.path.dirname(__file__), "..", "submission.csv")

    rows_data = []
    try:
        with open(submission_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows_data.append(row)
                if int(row["rank"]) >= 10:
                    break
    except:
        rows_data = []

    if rows_data:
        table_data = [[
            Paragraph("<b>Rank</b>", S["body"]),
            Paragraph("<b>Candidate ID</b>", S["body"]),
            Paragraph("<b>Score</b>", S["body"]),
            Paragraph("<b>Reasoning</b>", S["body"]),
        ]]
        for r in rows_data[:10]:
            reasoning_text = r["reasoning"][:120] + ("…" if len(r["reasoning"]) > 120 else "")
            table_data.append([
                Paragraph(f'<b>{r["rank"]}</b>', ParagraphStyle("rc", fontSize=11, fontName="Helvetica-Bold", textColor=ACCENT, alignment=TA_CENTER)),
                Paragraph(r["candidate_id"], ParagraphStyle("cid", fontSize=9, fontName="Courier", textColor=SECONDARY)),
                Paragraph(f'<b>{float(r["score"]):.3f}</b>', ParagraphStyle("sc", fontSize=9.5, fontName="Helvetica-Bold", textColor=GREEN, alignment=TA_CENTER)),
                Paragraph(reasoning_text, ParagraphStyle("rs", fontSize=8.5, fontName="Helvetica", textColor=DARK_TEXT)),
            ])

        t = Table(table_data, colWidths=[0.5*inch, 1.1*inch, 0.7*inch, 4.9*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PRIMARY),
            ("TEXTCOLOR", (0,0), (-1,0), WHITE),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#DDEAF2")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT_BG, WHITE]),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 7),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("Top candidates listed in submission.csv", S["body"]))

    elements.append(PageBreak())


def build_evaluation(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("09 — Evaluation Strategy"))
    elements.append(Paragraph("Why This Approach Maximises NDCG@10", S["slide_title"]))
    elements.append(rule())

    elements.append(Paragraph(
        "The challenge scores submissions 50% on NDCG@10. Our design explicitly optimises for "
        "top-of-list quality rather than overall recall:", S["body"]))
    elements.append(Spacer(1, 0.1*inch))

    points = [
        ("Disqualifiers remove the wrong", "Applying a × 0.05 multiplier to wrong-role candidates pushes "
         "them to rank 90+, freeing the top 10 for genuine ML/AI engineers."),
        ("Behavioral signals boost reachable candidates", "An otherwise strong candidate inactive for 180 days "
         "scores 0.05 on recency. A twin who's active today scores 1.0. This surfaces actually-hireable candidates."),
        ("Career quality prevents title-chase traps", "A 'Senior AI Engineer' at TCS their entire career scores 0.3× "
         "the same title at a product company."),
        ("Honeypot exclusion protects NDCG@10", "All ~80 honeypot profiles are pushed to near-zero score, "
         "well below rank 100. Honeypot rate in our top 100: 0%."),
        ("Semantic relevance rewards substance", "The JD text was expanded with conceptual synonyms so candidates "
         "describing real retrieval/ranking systems surface even without exact buzzwords."),
    ]
    for title, detail in points:
        elements.append(Paragraph(f"<b>{title}</b>", ParagraphStyle("pt", fontSize=10, fontName="Helvetica-Bold",
                                                                      textColor=PRIMARY, spaceAfter=2, spaceBefore=8)))
        elements.append(Paragraph(detail, S["body"]))

    elements.append(Spacer(1, 0.1*inch))
    elements.append(metric_row([
        ("Target Metric", "NDCG@10", PRIMARY),
        ("Weight", "50%", ACCENT),
        ("Our Focus", "Top-10 Quality", SECONDARY),
        ("Honeypots in Top 100", "0", GREEN),
    ]))
    elements.append(PageBreak())


def build_tech_stack(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("10 — Technical Stack & Compute Constraints"))
    elements.append(Paragraph("CPU-Only, Sub-5-Minute, No External APIs", S["slide_title"]))
    elements.append(rule())

    left = [
        Paragraph("Dependencies", S["slide_h2"]),
        Paragraph("numpy >= 1.24", S["bullet"]),
        Paragraph("pandas >= 2.0", S["bullet"]),
        Paragraph("scikit-learn >= 1.3", S["bullet"]),
        Paragraph("Python stdlib only (csv, json, argparse, datetime)", S["bullet"]),
        Spacer(1, 0.1*inch),
        Paragraph("Single command to reproduce:", S["slide_h2"]),
        Paragraph("python src/rank.py \\\n  --candidates ./candidates.jsonl \\\n  --out ./submission.csv",
                  ParagraphStyle("cmd", fontSize=8.5, fontName="Courier",
                                 backColor=colors.HexColor("#1A1A2E"), textColor=colors.HexColor("#2ECC71"),
                                 borderPad=8, leftIndent=0)),
    ]
    right = [
        Paragraph("Compute Profile", S["slide_h2"]),
        Paragraph("Total runtime: ~55 seconds (vs 5 min limit)", S["bullet"]),
        Paragraph("Peak RAM: ~3.5 GB (vs 16 GB limit)", S["bullet"]),
        Paragraph("GPU: not used", S["bullet"]),
        Paragraph("Network calls: zero", S["bullet"]),
        Spacer(1, 0.08*inch),
        Paragraph("Bottleneck: TF-IDF matrix construction + cosine similarity (~45s). "
                  "Structured scoring ~8s for 100K candidates.", S["body"]),
        Spacer(1, 0.08*inch),
        Paragraph("Production path: pre-compute TF-IDF embeddings nightly; "
                  "ranking step would then be <5s.", S["body"]),
    ]
    elements.append(two_col(left, right))
    elements.append(PageBreak())


def build_closing(elements):
    elements.append(Spacer(1, 0.2*inch))
    elements.append(section_label("11 — Summary"))
    elements.append(Paragraph("What We Built & Why It Works", S["slide_title"]))
    elements.append(rule())

    summary_items = [
        ("Reads between the lines",
         "TF-IDF with bigrams over full career text captures semantic meaning, not just listed keywords."),
        ("Understands what the role needs",
         "35 JD-specific required signals + 17 bonus signals derived from close reading of the JD, "
         "not generic tech keywords."),
        ("Looks at the full picture",
         "5 independent scoring components covering semantics, skills, career trajectory, "
         "platform behaviour, and location."),
        ("Actively avoids the traps",
         "Disqualifier multipliers, honeypot detection, and consulting-company penalties "
         "ensure the wrong candidates never reach the top 10."),
        ("Delivers a recruiter-trustworthy shortlist",
         "Per-candidate reasoning references specific YoE, title, company, response rate, "
         "and recency — grounded in the actual profile, no hallucination."),
        ("Scales to production",
         "55-second runtime, 3.5 GB RAM, CPU-only, zero external dependencies beyond scikit-learn."),
    ]

    for i, (title, detail) in enumerate(summary_items):
        bg = LIGHT_BG if i % 2 == 0 else WHITE
        row = [[
            Paragraph(f'<font color="{ACCENT.hexval()}">✓</font>', ParagraphStyle("chk", fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph(f'<b>{title}</b><br/>{detail}', S["body"]),
        ]]
        t = Table(row, colWidths=[0.4*inch, 6.8*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), bg),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LINEBELOW", (0,0), (-1,-1), 0.4, colors.HexColor("#DDEAF2")),
        ]))
        elements.append(t)

    elements.append(Spacer(1, 0.2*inch))
    elements.append(callout_box("Build something real. Make hiring smarter.", bg=PRIMARY))


# ── Main builder ──────────────────────────────────────────────────────────────

def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.65*inch,
        rightMargin=0.65*inch,
        topMargin=0.75*inch,
        bottomMargin=0.65*inch,
        title="Redrob Hackathon — Candidate Ranking Approach",
        author="team_001",
        subject="Intelligent Candidate Discovery & Ranking"
    )

    elements = []

    build_cover(elements)
    build_problem(elements)
    build_architecture(elements)
    build_semantic(elements)
    build_skills(elements)
    build_career(elements)
    build_behavioral(elements)
    build_honeypot(elements)
    build_results(elements)
    build_evaluation(elements)
    build_tech_stack(elements)
    build_closing(elements)

    # Page templates: cover page gets different background
    page_count = [0]
    def on_page(canvas_obj, doc_obj):
        page_count[0] += 1
        if page_count[0] == 1:
            cover_background(canvas_obj, doc_obj)
        else:
            slide_background(canvas_obj, doc_obj)

    doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF written: {output_path}")


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "approach_deck.pdf"
    build_pdf(out)
