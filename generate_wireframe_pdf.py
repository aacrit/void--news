#!/usr/bin/env python3
"""
void --news: CEO Visual Architecture & Wireframe Document (v2)
Accurate wireframes from code exploration + all UAT fixes applied.

Pages:
  1. Cover
  2. System Architecture
  3. Data Flow Diagram
  4. Pipeline Process Flow
  5. Frontend Wireframe — Desktop Homepage
  6. Frontend Wireframe — DeepDive Modal
  7. Frontend Wireframe — Mobile + Other Pages
  8. Component Dependency Map
  9. Database Schema + Bias Engine
  10. Optimization Opportunities
"""

import math
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

W, H = landscape(A4)  # 841.89 x 595.28
MARGIN = 35
TOTAL_PAGES = 10


# ── Color Palette ─────────────────────────────────────────────────────────
class C:
    bg = HexColor("#0F0F0F")
    bg_light = HexColor("#1A1A1A")
    bg_card = HexColor("#222222")
    bg_section = HexColor("#181818")

    amber = HexColor("#D4A853")
    amber_dim = HexColor("#A07830")
    amber_bright = HexColor("#F0C860")

    text = HexColor("#E8E0D0")
    text_dim = HexColor("#9A9080")
    text_muted = HexColor("#706050")

    blue = HexColor("#4A90D9")
    green = HexColor("#4CAF50")
    red = HexColor("#E74C3C")
    orange = HexColor("#F39C12")
    purple = HexColor("#9B59B6")
    teal = HexColor("#1ABC9C")
    pink = HexColor("#E91E63")
    cyan = HexColor("#00BCD4")

    lean_far_left = HexColor("#1565C0")
    lean_left = HexColor("#42A5F5")
    lean_center_left = HexColor("#90CAF9")
    lean_center = HexColor("#B0BEC5")
    lean_center_right = HexColor("#EF9A9A")
    lean_right = HexColor("#EF5350")
    lean_far_right = HexColor("#C62828")

    flow_rss = HexColor("#FF9800")
    flow_pipeline = HexColor("#2196F3")
    flow_db = HexColor("#4CAF50")
    flow_frontend = HexColor("#9C27B0")
    flow_external = HexColor("#F44336")

    dup_high = HexColor("#E74C3C")
    dup_medium = HexColor("#F39C12")
    dup_low = HexColor("#4CAF50")


# ── Drawing Helpers ───────────────────────────────────────────────────────

def draw_bg(c):
    c.setFillColor(C.bg)
    c.rect(0, 0, W, H, fill=1, stroke=0)


def draw_page_number(c, page_num):
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 8)
    c.drawRightString(W - MARGIN, 20, f"void --news  |  page {page_num}/{TOTAL_PAGES}")


def rounded_rect(c, x, y, w, h, r=6, fill=None, stroke=None, stroke_width=0.5):
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(stroke_width)
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    if fill and stroke:
        c.drawPath(p, fill=1, stroke=1)
    elif fill:
        c.drawPath(p, fill=1, stroke=0)
    elif stroke:
        c.drawPath(p, fill=0, stroke=1)


def draw_arrow(c, x1, y1, x2, y2, color=None, head_size=6, width=1.5, dashed=False):
    if color:
        c.setStrokeColor(color)
        c.setFillColor(color)
    c.setLineWidth(width)
    if dashed:
        c.setDash(4, 3)
    else:
        c.setDash()
    c.line(x1, y1, x2, y2)
    c.setDash()
    angle = math.atan2(y2 - y1, x2 - x1)
    ax1 = x2 - head_size * math.cos(angle - math.pi / 6)
    ay1 = y2 - head_size * math.sin(angle - math.pi / 6)
    ax2 = x2 - head_size * math.cos(angle + math.pi / 6)
    ay2 = y2 - head_size * math.sin(angle + math.pi / 6)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(ax1, ay1)
    p.lineTo(ax2, ay2)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def box_with_label(c, x, y, w, h, label, sublabel=None, fill=None, border=None,
                   font_size=9, sublabel_size=7, text_color=None):
    fill = fill or C.bg_card
    border = border or C.text_muted
    text_color = text_color or C.text
    rounded_rect(c, x, y, w, h, r=4, fill=fill, stroke=border, stroke_width=0.8)
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(x + w / 2, y + h / 2 + (4 if sublabel else 0), label)
    if sublabel:
        c.setFont("Helvetica", sublabel_size)
        c.setFillColor(C.text_dim)
        c.drawCentredString(x + w / 2, y + h / 2 - 10, sublabel)


def section_title(c, x, y, title_text, color=None):
    """[F05 fix] Use pdfmetrics for exact underline width."""
    color = color or C.amber
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, title_text)
    tw = pdfmetrics.stringWidth(title_text, "Helvetica-Bold", 14)
    c.setStrokeColor(color)
    c.setLineWidth(0.5)
    c.line(x, y - 4, x + tw, y - 4)


def badge(c, x, y, text, color, text_color=None):
    text_color = text_color or white
    tw = pdfmetrics.stringWidth(text, "Helvetica-Bold", 7) + 12
    rounded_rect(c, x, y - 4, tw, 14, r=3, fill=color)
    c.setFillColor(text_color)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x + tw / 2, y, text)
    return tw


def legend_item(c, x, y, color, label):
    c.setFillColor(color)
    c.circle(x + 4, y + 3, 4, fill=1, stroke=0)
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 7.5)
    c.drawString(x + 12, y, label)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 1: COVER
# ══════════════════════════════════════════════════════════════════════════
def page_cover(c):
    draw_bg(c)

    # Decorative border
    c.setStrokeColor(C.amber_dim)
    c.setLineWidth(0.5)
    c.rect(30, 30, W - 60, H - 60, fill=0, stroke=1)
    c.rect(34, 34, W - 68, H - 68, fill=0, stroke=1)

    cy = H / 2 + 80
    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 42)
    c.drawCentredString(W / 2, cy, "void --news")

    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 14)
    c.drawCentredString(W / 2, cy - 30, "Architecture & Wireframe Visual Reference")

    c.setStrokeColor(C.amber_dim)
    c.setLineWidth(0.3)
    c.line(W / 2 - 150, cy - 50, W / 2 + 150, cy - 50)

    items = [
        "System Architecture  |  Data Flow  |  Pipeline Process",
        "Frontend Wireframes  |  Component Map  |  Database Schema",
        "Bias Engine  |  Duplicate Analysis  |  Interaction Map"
    ]
    for i, item in enumerate(items):
        c.setFillColor(C.text_muted)
        c.setFont("Helvetica", 10)
        c.drawCentredString(W / 2, cy - 80 - i * 18, item)

    # Stats bar
    stats_y = cy - 160
    stats = [
        ("419", "Sources"),
        ("6", "Bias Axes"),
        ("5", "Pages"),
        ("38", "Components"),
        ("10", "DB Tables"),
        ("$0", "Ops Cost"),
    ]
    stat_w = 80
    start_x = W / 2 - (len(stats) * stat_w) / 2
    for i, (num, label) in enumerate(stats):
        sx = start_x + i * stat_w
        c.setFillColor(C.amber)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(sx + stat_w / 2, stats_y, num)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 8)
        c.drawCentredString(sx + stat_w / 2, stats_y - 15, label)

    # Footer
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, 55, "Confidential  |  March 2026  |  CEO Reference Document  |  v2.0")

    # [F10 fix] Uniform legend spacing
    ly = 100
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(60, ly + 15, "COLOR KEY:")
    x_positions = [60, 180, 300, 420, 540, 660]
    legend_data = [
        (C.dup_high, "Duplication / Overlap"),
        (C.dup_medium, "Shared / Connected"),
        (C.dup_low, "Clean / Unique"),
        (C.blue, "Data Flow"),
        (C.amber, "Key Metric"),
        (C.purple, "User Interaction"),
    ]
    for i, (color, label) in enumerate(legend_data):
        legend_item(c, x_positions[i], ly, color, label)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 2: SYSTEM ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════
def page_system_architecture(c):
    draw_bg(c)
    draw_page_number(c, 2)

    section_title(c, 40, H - 40, "SYSTEM ARCHITECTURE — High-Level Overview")

    # ── External services row ──
    y_ext = H - 100
    rounded_rect(c, 40, y_ext, 200, 50, fill=HexColor("#1B2838"), stroke=C.flow_rss)
    c.setFillColor(C.flow_rss)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(140, y_ext + 30, "419 RSS Sources")
    c.setFont("Helvetica", 8)
    c.setFillColor(C.text_dim)
    c.drawCentredString(140, y_ext + 14, "42 US Major | 181 Intl | 196 Indie")

    rounded_rect(c, 280, y_ext, 140, 50, fill=HexColor("#1B2838"), stroke=C.flow_external)
    c.setFillColor(C.flow_external)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(350, y_ext + 30, "Gemini 2.5 Flash")
    c.setFont("Helvetica", 8)
    c.setFillColor(C.text_dim)
    c.drawCentredString(350, y_ext + 14, "Free tier | ~60 calls/run")

    rounded_rect(c, 460, y_ext, 150, 50, fill=HexColor("#1B2838"), stroke=C.teal)
    c.setFillColor(C.teal)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(535, y_ext + 30, "GitHub Actions")
    c.setFont("Helvetica", 8)
    c.setFillColor(C.text_dim)
    c.drawCentredString(535, y_ext + 14, "4x daily cron | CI/CD")

    rounded_rect(c, 650, y_ext, 140, 50, fill=HexColor("#1B2838"), stroke=C.green)
    c.setFillColor(C.green)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(720, y_ext + 30, "GitHub Pages")
    c.setFont("Helvetica", 8)
    c.setFillColor(C.text_dim)
    c.drawCentredString(720, y_ext + 14, "Static hosting | CDN")

    # ── PIPELINE (center-left) ──
    y_pipe = y_ext - 150
    pipe_w = 350
    pipe_h = 110
    rounded_rect(c, 40, y_pipe, pipe_w, pipe_h, r=8, fill=HexColor("#142233"), stroke=C.flow_pipeline, stroke_width=1.5)
    c.setFillColor(C.flow_pipeline)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(60, y_pipe + pipe_h - 22, "Python Pipeline")
    c.setFont("Helvetica", 8)
    pipe_items = [
        "RSS Fetch (30 workers) -> Scrape (Playwright)",
        "Bias Analysis: 5 NLP Axes (rule-based, $0)",
        "Clustering: TF-IDF (threshold 0.2) + Entity Merge",
        "Summarize (Gemini 25 cap) -> Rank (10 signals v5.4)",
        "Daily Brief: TL;DR + Opinion + Audio (Gemini TTS)"
    ]
    for i, item in enumerate(pipe_items):
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 8)
        c.drawString(65, y_pipe + pipe_h - 40 - i * 14, item)

    # ── SUPABASE (below pipeline) ──
    y_db = y_pipe - 150
    db_w = 350
    db_h = 110
    rounded_rect(c, 40, y_db, db_w, db_h, r=8, fill=HexColor("#1A2E1A"), stroke=C.flow_db, stroke_width=1.5)
    c.setFillColor(C.flow_db)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(60, y_db + db_h - 22, "Supabase (PostgreSQL)")
    db_items = [
        "sources (419) | articles (100k+) | bias_scores",
        "story_clusters | cluster_articles (junction)",
        "categories | article_categories | pipeline_runs",
        "daily_briefs (TL;DR + audio) | source_topic_lean",
        "Views: cluster_bias_summary | RLS: public read"
    ]
    for i, item in enumerate(db_items):
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 8)
        c.drawString(65, y_db + db_h - 40 - i * 14, item)

    # ── FRONTEND (right side) ──
    y_fe = y_pipe - 50
    fe_w = 350
    fe_h = 200
    rounded_rect(c, 440, y_fe, fe_w, fe_h, r=8, fill=HexColor("#2A1A33"), stroke=C.flow_frontend, stroke_width=1.5)
    c.setFillColor(C.flow_frontend)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(460, y_fe + fe_h - 22, "Next.js 16 Static Site")

    fe_items = [
        ("/ (World)", "Homepage — importance-ranked news feed"),
        ("/us, /india", "Edition-specific feeds (section[] filter)"),
        ("/paper", "E-paper broadsheet layout"),
        ("/sources", "419-source political spectrum chart"),
        ("/command-center", "CEO KPI dashboard (14 cards, 4 domains)"),
        ("DeepDive modal", "Tabbed: Summary | AllSides | Scoring"),
        ("void --onair", "TL;DR + opinion + 2-voice audio player"),
    ]
    for i, (route, desc) in enumerate(fe_items):
        yy = y_fe + fe_h - 42 - i * 22
        c.setFillColor(C.amber)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(465, yy, route)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 7.5)
        c.drawString(570, yy, desc)

    # ── ARROWS ──
    draw_arrow(c, 140, y_ext, 140, y_pipe + pipe_h, C.flow_rss, width=2)
    draw_arrow(c, 350, y_ext, 280, y_pipe + pipe_h, C.flow_external, width=1.5, dashed=True)
    draw_arrow(c, 535, y_ext, 350, y_pipe + pipe_h, C.teal, width=1.5)
    draw_arrow(c, 215, y_pipe, 215, y_db + db_h, C.flow_pipeline, width=2)
    draw_arrow(c, 390, y_db + db_h / 2, 440, y_fe + 50, C.flow_db, width=2)
    # [F04 fix] Arrow angles downward into Frontend box
    draw_arrow(c, 720, y_ext, 620, y_fe + fe_h - 30, C.green, width=1.5)

    # ── Cost badge ──
    bx, by = 440, y_db + 10
    rounded_rect(c, bx, by, 200, 85, fill=HexColor("#1A2A1A"), stroke=C.green)
    c.setFillColor(C.green)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(bx + 15, by + 63, "$0 Operational Cost")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 8)
    for i, item in enumerate(["Bias analysis: rule-based NLP", "Gemini Flash free tier (~60 calls/run)", "GitHub Actions/Pages free", "Supabase free tier"]):
        c.drawString(bx + 15, by + 45 - i * 13, item)

    # ── Runtime badge ──
    rx, ry = 680, y_db + 10
    rounded_rect(c, rx, ry, 110, 85, fill=HexColor("#2A2010"), stroke=C.amber_dim)
    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(rx + 55, ry + 63, "Runtime")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 8)
    for i, line in enumerate(["Incremental: 25-35m", "Fresh DB: 108m", "Cron: 4x daily", "Audio: 2x daily"]):
        c.drawCentredString(rx + 55, ry + 45 - i * 13, line)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 3: DATA FLOW DIAGRAM
# ══════════════════════════════════════════════════════════════════════════
def page_data_flow(c):
    draw_bg(c)
    draw_page_number(c, 3)

    section_title(c, 40, H - 40, "DATA FLOW — From Source to Screen")

    cols = [
        ("INGEST", C.flow_rss, [
            ("419 RSS\nFeeds", "rss_fetcher.py\n30 parallel workers"),
            ("Web\nScraper", "web_scraper.py\nPlaywright Chrome"),
            ("Dedup\nFilter", "deduplicator.py\n48h URL + semantic"),
        ]),
        ("ANALYZE", C.flow_pipeline, [
            ("Political\nLean", "Keyword lexicons\nEntity sentiment"),
            ("Sensation-\nalism", "Clickbait patterns\nSuperlative density"),
            ("Opinion vs\nReporting", "14 attribution patterns\nSubjectivity score"),
            ("Factual\nRigor", "Named sources (NER)\nOrg citations"),
            ("Framing", "50+ synonym pairs\nOmission detection"),
        ]),
        ("CLUSTER", C.teal, [
            ("TF-IDF\nVectorize", "5K features, 1-2 grams\nThreshold 0.2"),
            ("Entity\nMerge", "NER overlap\n3+ shared entities"),
            ("Gemini\nReasoning", "25-call budget\nPer-axis context"),
            ("Cluster\nSummary", "Headline + consensus\n250-350 words"),
        ]),
        ("RANK", C.amber, [
            ("10-Signal\nRanker v5.4", "BIAS-BLIND\nWeights sum = 1.0"),
            ("Category\nDesk", "7 categories\nAuto-mapped"),
            ("Editorial\nTriage", "Topic diversity\nSame-event cap 3"),
            ("Daily\nBrief", "TL;DR + Opinion\n+ 2-voice Audio"),
        ]),
        ("STORE", C.flow_db, [
            ("articles\ntable", "URL, title, text\n300-char excerpt"),
            ("bias_scores\ntable", "5 axes x 0-100\nrationale JSONB"),
            ("story_\nclusters", "summary, rank\nsections text[]"),
            ("daily_\nbriefs", "TL;DR, audio_url\nper-edition"),
        ]),
        ("DISPLAY", C.flow_frontend, [
            ("Desktop\nFeed", "3-zone layout\nLead+Digest+Wire"),
            ("DeepDive\nModal", "3 tabs: Summary\nAllSides | Scoring"),
            ("Daily\nBrief", "SkyboxBanner +\nOnAir audio player"),
            ("Sources\nPage", "SpectrumChart\n419 sources"),
        ]),
    ]

    col_w = (W - 80) / len(cols)
    start_y = H - 80

    for ci, (title, color, items) in enumerate(cols):
        cx = 40 + ci * col_w

        # Column header
        rounded_rect(c, cx + 5, start_y - 5, col_w - 10, 22, fill=color)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(cx + col_w / 2, start_y, title)

        item_h = 55
        gap = 8
        for ii, (name, detail) in enumerate(items):
            iy = start_y - 40 - ii * (item_h + gap)
            rounded_rect(c, cx + 8, iy, col_w - 16, item_h, fill=C.bg_card, stroke=color, stroke_width=0.6)

            lines = name.split("\n")
            c.setFillColor(color)
            c.setFont("Helvetica-Bold", 8.5)
            for li, line in enumerate(lines):
                c.drawCentredString(cx + col_w / 2, iy + item_h - 14 - li * 11, line)

            dlines = detail.split("\n")
            c.setFillColor(C.text_dim)
            c.setFont("Helvetica", 7)
            for li, line in enumerate(dlines):
                c.drawCentredString(cx + col_w / 2, iy + 16 - li * 10, line)

        # [F03 fix] Arrows between header and first item, not through items
        if ci < len(cols) - 1:
            arr_y = start_y + 3
            draw_arrow(c, cx + col_w - 3, arr_y, cx + col_w + 3, arr_y, C.text_muted, width=1.5)

    # Bottom: duplication indicators — [F13 fix] reduced spacing
    dy = 38
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(40, dy + 12, "DUPLICATION ANALYSIS:")

    dup_items = [
        (C.dup_high, "bias_scores rationale + gemini_reasoning: overlapping fields"),
        (C.dup_medium, "cluster summary + daily brief TL;DR: both summarize clusters"),
        (C.dup_low, "Feed page + Paper page: same data, different layout (by design)"),
    ]
    for i, (color, text) in enumerate(dup_items):
        c.setFillColor(color)
        c.circle(55 + i * 250, dy, 4, fill=1, stroke=0)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6.5)
        c.drawString(63 + i * 250, dy - 3, text)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 4: PIPELINE PROCESS FLOW
# ══════════════════════════════════════════════════════════════════════════
def page_pipeline_flow(c):
    draw_bg(c)
    draw_page_number(c, 4)

    section_title(c, 40, H - 40, "PIPELINE PROCESS FLOW — 10-Step Execution (4x Daily)")

    steps = [
        ("1", "LOAD\nSOURCES", "sources.json\n419 -> Supabase", C.flow_rss, "1-2 min"),
        ("2", "FETCH\nRSS", "30 parallel workers\n~3000 articles/run", C.flow_rss, "3-5 min"),
        ("3", "SCRAPE\nTEXT", "Playwright Chrome\n30 workers", C.flow_rss, "5-8 min"),
        ("4", "DEDUP\nFILTER", "48h URL + semantic\nNear-dupe detection", C.teal, "< 1 min"),
        ("5", "ANALYZE\nBIAS", "5 NLP axes, 8 workers\nRule-based ($0)", C.flow_pipeline, "3-5 min"),
        ("6", "CLUSTER\nSTORIES", "TF-IDF 0.2 thresh\n+ entity merge", C.teal, "2-3 min"),
        ("7", "GEMINI\nENRICH", "25 reason + 25 summary\n+ 3 triage calls", C.flow_external, "8-12 min"),
        ("8", "RANK +\nCATEGORIZE", "10-signal ranker v5.4\n7 categories + gates", C.amber, "1-2 min"),
        ("9", "DAILY\nBRIEF", "TL;DR + Opinion\n+ 2-voice TTS", C.purple, "3-5 min"),
        ("10", "CLEANUP\n& STORE", "Enrich 8 workers\n7d articles, 2d clusters", C.flow_db, "1-2 min"),
    ]

    box_w = 135
    box_h = 80
    gap_x = 18
    start_x = 50
    row1_y = H - 120
    row2_y = row1_y - box_h - 80  # [F01 fix] Proper gap for snake flow

    for i, (num, title, detail, color, time) in enumerate(steps):
        row = i // 5
        col = i % 5

        if row == 0:
            x = start_x + col * (box_w + gap_x)
            y = row1_y
        else:
            # Row 2 reversed for snake flow
            x = start_x + (4 - col) * (box_w + gap_x)
            y = row2_y

        # Step box
        rounded_rect(c, x, y, box_w, box_h, r=6, fill=C.bg_card, stroke=color, stroke_width=1.2)

        # Step number badge
        c.setFillColor(color)
        c.circle(x + 15, y + box_h - 12, 10, fill=1, stroke=0)
        c.setFillColor(C.bg)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x + 15, y + box_h - 16, num)

        # Title
        lines = title.split("\n")
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 9)
        for li, line in enumerate(lines):
            c.drawString(x + 30, y + box_h - 14 - li * 12, line)

        # Detail
        dlines = detail.split("\n")
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 7.5)
        for li, line in enumerate(dlines):
            c.drawString(x + 10, y + 22 - li * 11, line)

        # Time badge
        badge(c, x + box_w - 50, y + 5, time, HexColor("#333333"), C.text_dim)

        # Arrows within row 1 (left to right)
        if row == 0 and col < 4:
            draw_arrow(c, x + box_w + 2, y + box_h / 2, x + box_w + gap_x - 2, y + box_h / 2, C.text_muted, width=1.5)

        # [F01 fix] Arrow from step 5 (row 1 rightmost) down to step 6 (row 2 rightmost)
        if i == 4:
            step6_x = start_x + 4 * (box_w + gap_x)
            draw_arrow(c, x + box_w / 2, y, step6_x + box_w / 2, row2_y + box_h, C.text_muted, width=1.5)

        # Arrows within row 2 (right to left)
        if row == 1 and col < 4:
            draw_arrow(c, x - 2, y + box_h / 2, x - gap_x + 2, y + box_h / 2, C.text_muted, width=1.5)

    # ── Timing summary ──
    ty = row2_y - 60
    rounded_rect(c, 50, ty, 700, 50, fill=C.bg_section, stroke=C.amber_dim)
    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(70, ty + 32, "PIPELINE TIMING")

    timings = [
        ("Total (incremental)", "25-35 min"),
        ("Total (fresh DB)", "108 min"),
        ("Gemini API alone", "~20 min"),
        ("Non-audio runs", "00:00 + 12:00 UTC"),
        ("Audio runs", "06:00 + 18:00 UTC"),
    ]
    tx = 70
    for label, val in timings:
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 8)
        c.drawString(tx, ty + 12, label)
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(tx, ty + 2, val)
        tx += 140

    # ── Gemini budget ──
    gy = ty - 50
    rounded_rect(c, 50, gy, 350, 35, fill=C.bg_section, stroke=C.flow_external)
    c.setFillColor(C.flow_external)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(65, gy + 18, "GEMINI BUDGET:")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 8)
    c.drawString(175, gy + 18, "25 reasoning + 25 summarization + 3 triage")
    c.drawString(175, gy + 5, "6 brief calls (separate budget) | 15 RPM rate limit")

    # [F06 fix] Callout with taller box
    rounded_rect(c, 430, gy, 320, 45, fill=HexColor("#2A1515"), stroke=C.dup_high)
    c.setFillColor(C.dup_high)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(445, gy + 28, "OVERLAP: Steps 7+9")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 7.5)
    c.drawString(445, gy + 15, "Gemini summaries (step 7) and brief TL;DR (step 9)")
    c.drawString(445, gy + 4, "both summarize top clusters. Could cascade content.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE 5: HOMEPAGE WIREFRAME (Desktop)
# ══════════════════════════════════════════════════════════════════════════
def page_wireframe_homepage(c):
    draw_bg(c)
    draw_page_number(c, 5)

    section_title(c, 40, H - 40, "WIREFRAME — Desktop Homepage (Accurate from Code)")

    # Main wireframe area
    wx, wy = 40, 40
    ww, wh = 480, H - 100

    rounded_rect(c, wx, wy, ww, wh, r=4, fill=HexColor("#1A1A18"), stroke=C.text_muted, stroke_width=0.5)

    # ── NavBar (2 rows from code) ──
    ny = wy + wh - 50
    rounded_rect(c, wx + 5, ny, ww - 10, 45, fill=C.bg_card, stroke=C.amber_dim, stroke_width=0.3)
    # Row 1: Logo | Dateline | PageToggle + Theme
    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(wx + 15, ny + 28, "void --news")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 6)
    c.drawString(wx + 110, ny + 30, "Mar 30 | 3:47 PM")
    c.drawRightString(wx + ww - 15, ny + 30, "Sources | Theme")
    # Row 2: Edition pills | Sep | Lean chips | Sep | Topics dropdown
    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(wx + 15, ny + 10, "World")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 6)
    c.drawString(wx + 48, ny + 10, "US   India")
    c.drawString(wx + 110, ny + 10, "|")
    # Lean dots
    for j, (lbl, col) in enumerate([("L", C.lean_left), ("C", C.lean_center), ("R", C.lean_right)]):
        c.setFillColor(col)
        c.circle(wx + 125 + j * 25, ny + 13, 3, fill=1, stroke=0)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 5)
        c.drawString(wx + 130 + j * 25, ny + 10, lbl)
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 6)
    c.drawString(wx + 210, ny + 10, "|  Topics v")

    # ── SkyboxBanner (from code: 2 columns TL;DR + Opinion + OnAir) ──
    sy = ny - 62
    rounded_rect(c, wx + 5, sy, ww - 10, 57, fill=HexColor("#1A1A14"), stroke=C.amber_dim, stroke_width=0.5)
    # TL;DR column (left)
    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(wx + 12, sy + 44, "void --tl;dr")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 5.5)
    c.drawString(wx + 75, sy + 44, "2h ago")
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(wx + 12, sy + 32, "Markets Wobble as Fed Signals Hold")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 5.5)
    c.drawString(wx + 12, sy + 22, "Markets wobble as the Fed holds rates for the seventh")
    c.drawString(wx + 12, sy + 14, "consecutive meeting. Ukraine talks stall in Geneva...")
    # Opinion column (right, behind dotted divider)
    c.setStrokeColor(C.text_muted)
    c.setLineWidth(0.3)
    c.setDash(2, 2)
    c.line(wx + ww / 2, sy + 8, wx + ww / 2, sy + 50)
    c.setDash()
    c.setFillColor(C.amber_dim)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(wx + ww / 2 + 8, sy + 44, "void --opinion")
    rounded_rect(c, wx + ww / 2 + 75, sy + 41, 28, 10, r=3, fill=C.lean_left)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(wx + ww / 2 + 89, sy + 43, "left")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 5.5)
    c.drawString(wx + ww / 2 + 8, sy + 32, "The Fed's inaction speaks louder")
    c.drawString(wx + ww / 2 + 8, sy + 22, "than any rate cut would...")
    # OnAir pill (centered below columns)
    pill_x = wx + ww / 2 - 55
    rounded_rect(c, pill_x, sy + 2, 110, 14, r=7, fill=C.amber_dim)
    c.setFillColor(C.bg)
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(pill_x + 55, sy + 6, "void --onair  5:32")

    # ── ZONE 1: Lead Stories (2fr | 1fr grid from code) ──
    z1y = sy - 125
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 6)
    c.drawString(wx + 8, z1y + 120, "ZONE 1 — Lead (2fr | 1fr grid)")

    # Primary lead (2/3 width)
    lead_w = (ww - 20) * 2 / 3
    rounded_rect(c, wx + 5, z1y, lead_w, 115, fill=C.bg_card, stroke=C.text_muted, stroke_width=0.3)
    # Top-right badge
    badge(c, wx + lead_w - 55, z1y + 100, "Top Story", C.amber_dim)
    # Headline (Playfair Display ~48px mapped to wireframe)
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(wx + 15, z1y + 85, "Fed Holds Steady as Markets")
    c.drawString(wx + 15, z1y + 72, "Digest Inflation Data")
    # Summary
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 6)
    c.drawString(wx + 15, z1y + 55, "The Federal Reserve held its benchmark interest rate at 5.25-5.5%")
    c.drawString(wx + 15, z1y + 46, "for the seventh consecutive meeting. Markets dipped 0.8%...")
    # Footer: category | time ... Sigil
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 5.5)
    c.drawString(wx + 15, z1y + 10, "Economy | 2h ago")
    # Sigil (lean label + colored mark)
    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(wx + 15, z1y + 22, "Center")
    c.setFillColor(C.amber_dim)
    c.circle(wx + lead_w - 25, z1y + 15, 8, fill=1, stroke=0)
    c.setFillColor(C.bg)
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(wx + lead_w - 25, z1y + 13, "S")

    # Secondary lead (1/3 width)
    sec_x = wx + 5 + lead_w + 5
    sec_w = (ww - 20) / 3 - 5
    rounded_rect(c, sec_x, z1y, sec_w, 115, fill=C.bg_card, stroke=C.text_muted, stroke_width=0.3)
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(sec_x + 8, z1y + 95, "Ukraine Talks")
    c.drawString(sec_x + 8, z1y + 84, "Collapse After")
    c.drawString(sec_x + 8, z1y + 73, "Three Hours")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 5.5)
    c.drawString(sec_x + 8, z1y + 55, "8 sources | Conflict")
    c.drawString(sec_x + 8, z1y + 45, "Reuters, BBC,")
    c.drawString(sec_x + 8, z1y + 36, "Al Jazeera, DW...")
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 5)
    c.drawString(sec_x + 8, z1y + 10, "Conflict | 3h ago")
    c.setFillColor(C.amber_dim)
    c.circle(sec_x + sec_w - 15, z1y + 15, 6, fill=1, stroke=0)

    # ── ZONE 2: Digest Rows (colored left border, from code) ──
    z2y = z1y - 75
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 6)
    c.drawString(wx + 8, z2y + 70, "ZONE 2 — Digest Rows (6px color border)")

    cat_colors = [C.blue, C.orange, C.green, C.red]
    titles = [
        "China GDP beats expectations at 5.4% growth",
        "SpaceX Starship completes orbital test flight",
        "WHO warns of new H5N1 variant spreading in poultry",
        "Supreme Court takes up AI copyright case"
    ]
    sources_text = ["6 src | Economy", "4 src | Science", "5 src | Health", "7 src | Politics"]
    for i in range(4):
        ry = z2y + 55 - i * 16
        # Colored left border
        c.setStrokeColor(cat_colors[i])
        c.setLineWidth(3)
        c.line(wx + 10, ry - 1, wx + 10, ry + 12)
        # Category + time
        c.setFillColor(C.text_muted)
        c.setFont("Helvetica", 5)
        c.drawString(wx + 18, ry + 8, sources_text[i])
        # Headline (Playfair)
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(wx + 110, ry + 3, titles[i])
        # Sigil (sm)
        c.setFillColor(C.amber_dim)
        c.circle(wx + 462, ry + 6, 3, fill=1, stroke=0)

    # ── ZONE 3: Wire Grid (4-5 col from code) ──
    z3y = z2y - 58
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 6)
    c.drawString(wx + 8, z3y + 53, "ZONE 3 — Wire Grid (dot + cat + headline)")

    wire_w = (ww - 30) / 4
    for i in range(4):
        for j in range(2):
            bx = wx + 8 + i * (wire_w + 3)
            by = z3y + 28 - j * 25
            rounded_rect(c, bx, by, wire_w, 22, fill=C.bg_card, stroke=C.text_muted, stroke_width=0.2)
            # 6px dot
            c.setFillColor([C.blue, C.red, C.green, C.orange][i])
            c.circle(bx + 7, by + 11, 3, fill=1, stroke=0)
            c.setFillColor(C.text_dim)
            c.setFont("Helvetica", 4.5)
            c.drawString(bx + 14, by + 12, ["Econ", "Conf", "Sci", "Pol"][i])
            c.setFillColor(C.text)
            c.setFont("Helvetica", 5)
            c.drawString(bx + 14, by + 4, "Story headline...")

    # ── Footer ──
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 5)
    c.drawCentredString(wx + ww / 2, wy + 8, "World Edition / 487 stories | void --news | 419 sources")

    # ── RIGHT SIDE: Annotations ──
    ax = 540

    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(ax, H - 70, "Key Interactions (from code)")

    interactions = [
        (C.purple, "Click any story card", "Opens DeepDive modal (FLIP morph)"),
        (C.amber, "Click edition pill", "Filters by section[] in Supabase"),
        (C.blue, "Click Topics dropdown", "8 categories (All, Politics...)"),
        (C.green, "Click OnAir pill", "Expands radio player + waveform"),
        (C.teal, "Hover Sigil", "4-stage popup (spectrum/ring/scores)"),
        (C.orange, "Click TL;DR / Opinion", "Expands that column full-width"),
        (C.pink, "Scroll down", "IntersectionObserver infinite scroll"),
        (C.flow_external, "Theme toggle", "Light/dark via CSS custom props"),
        (C.cyan, "J/K keys", "Navigate stories, Enter opens"),
    ]

    for i, (color, action, result) in enumerate(interactions):
        iy = H - 100 - i * 22
        c.setFillColor(color)
        c.circle(ax + 4, iy + 4, 4, fill=1, stroke=0)
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(ax + 14, iy + 4, action)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6.5)
        c.drawString(ax + 14, iy - 5, result)

    # Component list
    cy = H - 330
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(ax, cy, "Components (from code)")

    components = [
        ("NavBar", "2-row: Logo+dateline | Edition+Lean+Topics"),
        ("SkyboxBanner", "2-col TL;DR+Opinion | OnAir pill+radio"),
        ("DesktopFeed", "3-zone: Lead | Digest | Wire grid"),
        ("LeadStory", "Headline + summary + footer(cat+Sigil)"),
        ("DigestRow", "6px color border + headline + Sigil sm"),
        ("WireCard", "6px dot + category + headline"),
        ("Sigil", "SVG beam+circle mark + lean label"),
        ("DeepDive", "Modal overlay (tabbed, see page 6)"),
        ("Footer", "Logo + products + copyright"),
    ]

    for i, (comp, desc) in enumerate(components):
        ry = cy - 18 - i * 15
        c.setFillColor(C.amber)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(ax, ry, comp)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6)
        c.drawString(ax + 95, ry, desc)

    # Duplication callout
    dy = cy - 170
    rounded_rect(c, ax - 5, dy, 270, 40, fill=HexColor("#2A1515"), stroke=C.dup_high)
    c.setFillColor(C.dup_high)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(ax + 5, dy + 25, "Content Overlap Detected")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 6.5)
    c.drawString(ax + 5, dy + 13, "SkyboxBanner + MobileBriefPill both render TL;DR.")
    c.drawString(ax + 5, dy + 3, "Consider: share hook state, don't duplicate text.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE 6: DEEPDIVE WIREFRAME
# ══════════════════════════════════════════════════════════════════════════
def page_wireframe_deepdive(c):
    draw_bg(c)
    draw_page_number(c, 6)

    section_title(c, 40, H - 40, "WIREFRAME — DeepDive Modal (3-Tab Story Analysis)")

    # Main modal wireframe
    mx, my = 40, 45
    mw, mh = 460, H - 115

    rounded_rect(c, mx, my, mw, mh, r=8, fill=HexColor("#1C1C18"), stroke=C.amber_dim, stroke_width=1)

    # ── Header (from code: counter + arrows + close) ──
    hy = my + mh - 35
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 7)
    c.drawString(mx + 15, hy + 10, "5 of 123")
    c.drawString(mx + 70, hy + 10, "<  >")
    c.drawRightString(mx + mw - 15, hy + 10, "X close")
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(mx + 15, hy - 8, "Fed Holds Steady as Markets Digest Inflation Data")

    # ── Tab selector (from code: Summary | AllSides | Scoring) ──
    tab_y = hy - 28
    tabs = ["Summary", "AllSides", "Scoring"]
    tab_w = 80
    for i, tab in enumerate(tabs):
        tx = mx + 15 + i * (tab_w + 10)
        c.setFillColor(C.amber if i == 0 else C.text_muted)
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 8)
        c.drawString(tx, tab_y, tab)
        if i == 0:
            c.setStrokeColor(C.amber)
            c.setLineWidth(1.5)
            tw = pdfmetrics.stringWidth(tab, "Helvetica-Bold", 8)
            c.line(tx, tab_y - 3, tx + tw, tab_y - 3)

    # ── TAB 1 CONTENT: Summary ──
    # Headline
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 9)
    sy = tab_y - 25
    c.drawString(mx + 15, sy, "Fed Holds Steady as Markets Digest Inflation Data")

    # Summary text with expandable overflow
    # [F07 fix] Taller box (52pt)
    smy = sy - 70
    rounded_rect(c, mx + 10, smy, mw - 25, 52, fill=C.bg_section, stroke=C.text_muted, stroke_width=0.3)
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 6.5)
    lines = [
        "The Federal Reserve held its benchmark interest rate at 5.25-5.5% for",
        "the seventh consecutive meeting, as chair Jerome Powell cited persistent",
        "inflation pressures. Markets reacted with a 0.8% dip in the S&P 500,",
        "while Treasury yields rose to 4.65%. Economists remain split..."
    ]
    for i, line in enumerate(lines):
        c.drawString(mx + 18, smy + 37 - i * 9, line)

    # Category + time
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 5.5)
    c.drawString(mx + 15, smy - 8, "Economy | Updated 2h ago | 12 sources")

    # Press Analysis button
    pa_y = smy - 25
    rounded_rect(c, mx + 15, pa_y, 120, 16, r=3, fill=C.bg_card, stroke=C.purple, stroke_width=0.5)
    c.setFillColor(C.purple)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(mx + 75, pa_y + 4, "Press Analysis >")

    # ── BiasInspector panel (slides from right on click) ──
    bi_y = pa_y - 95
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(mx + 15, bi_y + 82, "PRESS ANALYSIS — Bias Scorecard (slide-out panel)")

    axes = [
        ("Political Lean", 45, C.lean_center, "Center"),
        ("Sensationalism", 22, C.green, "Low"),
        ("Factual Rigor", 78, C.green, "High"),
        ("Framing", 31, C.orange, "Light"),
    ]
    ax_w = (mw - 40) / 4
    for i, (name, score, color, label) in enumerate(axes):
        axx = mx + 15 + i * ax_w
        rounded_rect(c, axx, bi_y, ax_w - 5, 70, fill=C.bg_card, stroke=C.text_muted, stroke_width=0.3)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 5.5)
        c.drawCentredString(axx + ax_w / 2, bi_y + 58, name)
        # 5-dot scale
        for d in range(5):
            filled = d < int(score / 20)
            c.setFillColor(color if filled else C.bg_section)
            c.circle(axx + ax_w / 2 - 12 + d * 6, bi_y + 48, 2.5, fill=1, stroke=0)
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(axx + ax_w / 2, bi_y + 22, str(score))
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6)
        c.drawCentredString(axx + ax_w / 2, bi_y + 8, label)

    # ── TAB 2 preview: AllSides (consensus / diverge) ──
    av_y = bi_y - 80
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(mx + 15, av_y + 70, "TAB 2: AllSides — Consensus + Diverge + 3-Column Sources")

    # Left: Consensus
    c.setFillColor(C.green)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(mx + 15, av_y + 55, "Where sources converge")
    items_a = ["Fed holds rates at 5.25-5.5%", "Powell cites inflation", "S&P dipped 0.8%"]
    for i, item in enumerate(items_a):
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 5.5)
        c.drawString(mx + 20, av_y + 42 - i * 10, f"  {item}")

    # Right: Divergence
    c.setFillColor(C.red)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(mx + mw / 2, av_y + 55, "Key disagreements")
    items_d = ["Sept vs Dec cut timeline", "Jobs market interpretation", "Corporate bond impact"]
    for i, item in enumerate(items_d):
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 5.5)
        c.drawString(mx + mw / 2 + 5, av_y + 42 - i * 10, f"  {item}")

    # 3-column source view
    cols_3 = [("Left Sources", C.lean_left), ("Center Sources", C.lean_center), ("Right Sources", C.lean_right)]
    col3_w = (mw - 50) / 3
    for i, (lbl, col) in enumerate(cols_3):
        cx = mx + 15 + i * (col3_w + 5)
        cy = av_y + 2
        rounded_rect(c, cx, cy, col3_w, 14, fill=col)
        c.setFillColor(white if i != 1 else black)
        c.setFont("Helvetica-Bold", 5)
        c.drawCentredString(cx + col3_w / 2, cy + 4, lbl)

    # ── TAB 3 preview: Scoring (DeepDiveSpectrum) ──
    sp_y = av_y - 35
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(mx + 15, sp_y + 25, "TAB 3: Scoring — 7-Zone Spectrum + Source Grid")

    spectrum_colors = [C.lean_far_left, C.lean_left, C.lean_center_left, C.lean_center,
                       C.lean_center_right, C.lean_right, C.lean_far_right]
    spec_labels = ["Far L", "Left", "C-L", "Center", "C-R", "Right", "Far R"]
    bar_w = (mw - 40) / 7
    for i, (col, lbl) in enumerate(zip(spectrum_colors, spec_labels)):
        bx = mx + 15 + i * bar_w
        rounded_rect(c, bx, sp_y, bar_w - 2, 16, r=2, fill=col)
        c.setFillColor(white if i in [0, 1, 5, 6] else black)
        c.setFont("Helvetica", 5)
        c.drawCentredString(bx + bar_w / 2, sp_y + 5, lbl)

    # Sigil in footer
    c.setFillColor(C.amber_dim)
    c.circle(mx + 25, my + 12, 8, fill=1, stroke=0)
    c.setFillColor(C.bg)
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(mx + 25, my + 10, "S")
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 5)
    c.drawString(mx + 38, my + 10, "Sigil (aggregate cluster bias)")

    # ── RIGHT SIDE: Annotations ──
    anx = 530

    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(anx, H - 70, "DeepDive Interactions")

    interactions = [
        (C.purple, "< > arrows / J K keys", "Navigate prev/next cluster"),
        (C.amber, "X close / Escape", "Close: 380ms snappy spring"),
        (C.blue, "Tab: Summary", "Headline + summary + expand"),
        (C.green, "Tab: AllSides", "Consensus, diverge, 3-col sources"),
        (C.teal, "Tab: Scoring", "7-zone spectrum + source grid"),
        (C.orange, "Press Analysis btn", "Slide-out bias scorecard panel"),
        (C.pink, "Open animation", "FLIP morph 500ms bouncy spring"),
        (C.cyan, "Swipe L/R (mobile)", "Navigate stories on touch"),
    ]
    for i, (color, action, result) in enumerate(interactions):
        iy = H - 100 - i * 22
        c.setFillColor(color)
        c.circle(anx + 4, iy + 4, 4, fill=1, stroke=0)
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(anx + 14, iy + 4, action)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6.5)
        c.drawString(anx + 14, iy - 5, result)

    # Backend data
    bcy = H - 300
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(anx, bcy, "Backend Data Loaded")

    data = [
        (C.flow_db, "story_clusters", "summary, consensus, divergence"),
        (C.flow_db, "cluster_articles", "junction -> per-article bias"),
        (C.flow_db, "bias_scores", "5 axes + rationale JSONB"),
        (C.flow_db, "cluster_bias_summary", "view: aggregated scores"),
        (C.flow_external, "Gemini reasoning", "contextual axis explanations"),
    ]
    for i, (color, table, desc) in enumerate(data):
        ry = bcy - 18 - i * 16
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(anx, ry, table)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6.5)
        c.drawString(anx + 115, ry, desc)

    # Overlap callout
    oy = bcy - 115
    rounded_rect(c, anx - 5, oy, 270, 48, fill=HexColor("#2A2515"), stroke=C.dup_medium)
    c.setFillColor(C.dup_medium)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(anx + 5, oy + 33, "Progressive Disclosure (by design)")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 6.5)
    c.drawString(anx + 5, oy + 20, "Sigil (compact) -> BiasInspector (4-axis)")
    c.drawString(anx + 5, oy + 10, "-> DeepDiveSpectrum (full source grid)")
    c.drawString(anx + 5, oy + 0, "3 levels of same data: intentional disclosure.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE 7: MOBILE + OTHER PAGES
# ══════════════════════════════════════════════════════════════════════════
def page_wireframe_other_pages(c):
    draw_bg(c)
    draw_page_number(c, 7)

    # [F12 fix] Section title higher, wireframes start lower
    section_title(c, 40, H - 35, "WIREFRAMES — Mobile Feed | Sources | Command Center | Paper")

    # ── MOBILE FEED (from code: hero + pill + compact cards + bottom nav) ──
    mw_phone, mh_phone = 155, 370
    mx, my = 40, H - 450

    c.setFillColor(C.text_dim)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(mx, my + mh_phone + 12, "MOBILE (375px)")

    rounded_rect(c, mx, my, mw_phone, mh_phone, r=10, fill=HexColor("#1A1A18"), stroke=C.text_muted, stroke_width=0.8)

    # Status bar
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 4.5)
    c.drawString(mx + 8, my + mh_phone - 10, "9:41")
    c.drawRightString(mx + mw_phone - 8, my + mh_phone - 10, "LTE")

    # Compact navbar
    rounded_rect(c, mx + 5, my + mh_phone - 28, mw_phone - 10, 15, fill=C.bg_card)
    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(mx + mw_phone / 2, my + mh_phone - 24, "void --news")

    # Hero card (MobileStoryCard variant="hero" ~140px)
    hero_y = my + mh_phone - 100
    rounded_rect(c, mx + 8, hero_y, mw_phone - 16, 68, fill=C.bg_card, stroke=C.text_muted, stroke_width=0.3)
    badge(c, mx + 12, hero_y + 55, "Top Story", C.amber_dim)
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(mx + 12, hero_y + 42, "Fed Holds Steady as")
    c.drawString(mx + 12, hero_y + 33, "Markets Digest Data")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 5)
    c.drawString(mx + 12, hero_y + 20, "Markets wobble as the Fed holds")
    c.drawString(mx + 12, hero_y + 12, "rates for the seventh meeting...")
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 4.5)
    c.drawString(mx + 12, hero_y + 3, "Economy | 2h ago")
    c.setFillColor(C.amber_dim)
    c.circle(mx + mw_phone - 22, hero_y + 8, 5, fill=1, stroke=0)

    # Brief pill (MobileBriefPill collapsed)
    pill_y = hero_y - 18
    rounded_rect(c, mx + 8, pill_y, mw_phone - 16, 13, r=6, fill=C.amber_dim)
    c.setFillColor(C.bg)
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(mx + mw_phone / 2, pill_y + 4, "void --tl;dr | Today's brief  v")

    # Compact cards (MobileStoryCard variant="compact" ~72px each mapped to ~35px)
    titles = ["Ukraine Talks Collapse", "China GDP Beats 5.4%", "SpaceX Orbital Test", "WHO H5N1 Warning"]
    cats = ["Conflict | 3h", "Economy | 4h", "Science | 5h", "Health | 6h"]
    for i in range(4):
        cy = pill_y - 18 - i * 38
        rounded_rect(c, mx + 8, cy, mw_phone - 16, 33, fill=C.bg_card, stroke=C.text_muted, stroke_width=0.2)
        c.setFillColor(C.text_muted)
        c.setFont("Helvetica", 4.5)
        c.drawString(mx + 14, cy + 23, cats[i])
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(mx + 14, cy + 12, titles[i])
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 4)
        c.drawString(mx + 14, cy + 4, f"{8-i*2} sources")
        c.setFillColor(C.amber_dim)
        c.circle(mx + mw_phone - 20, cy + 15, 3.5, fill=1, stroke=0)
        # Caret icon
        c.setFillColor(C.text_muted)
        c.setFont("Helvetica", 5)
        c.drawRightString(mx + mw_phone - 12, cy + 12, ">")

    # Bottom nav (MobileBottomNav: Edition | Lean | Topic)
    rounded_rect(c, mx + 5, my + 5, mw_phone - 10, 22, fill=C.bg_card)
    nav_items = ["World v", "All v", "Topics v"]
    for i, tab in enumerate(nav_items):
        tx = mx + 15 + i * 48
        c.setFillColor(C.amber if i == 0 else C.text_muted)
        c.setFont("Helvetica", 5)
        c.drawCentredString(tx + 20, my + 12, tab)

    # ── SOURCES PAGE ──
    sw, sh = 175, 175
    sx, sy = 215, H - 245

    c.setFillColor(C.text_dim)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(sx, sy + sh + 12, "SOURCES (/sources)")

    rounded_rect(c, sx, sy, sw, sh, r=4, fill=HexColor("#1A1A18"), stroke=C.text_muted, stroke_width=0.5)

    c.setFillColor(C.amber)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(sx + 10, sy + sh - 15, "419 Sources")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 5)
    c.drawString(sx + 80, sy + sh - 15, "3 tiers | 7-point lean")

    # Toolbar: lean filter
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 5)
    c.drawString(sx + 10, sy + sh - 30, "Left  Center  Right")

    # Spectrum bar + distribution bars
    spec_y = sy + sh - 55
    bar_w = (sw - 20) / 7
    spectrum_colors = [C.lean_far_left, C.lean_left, C.lean_center_left, C.lean_center,
                       C.lean_center_right, C.lean_right, C.lean_far_right]
    spec_heights = [12, 22, 32, 55, 28, 20, 10]
    for i, (col, h) in enumerate(zip(spectrum_colors, spec_heights)):
        bx = sx + 10 + i * bar_w
        rounded_rect(c, bx, spec_y - h, bar_w - 2, h, r=2, fill=col)

    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 4)
    labels = ["Far L", "Left", "C-L", "Center", "C-R", "Right", "Far R"]
    for i, lbl in enumerate(labels):
        c.drawCentredString(sx + 10 + i * bar_w + bar_w / 2, spec_y - 62, lbl)

    # Tier breakdown
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 5)
    c.drawString(sx + 10, sy + 15, "US Major: 49  |  Intl: 178  |  Indie: 182")

    # ── COMMAND CENTER ──
    cw, ch = 175, 175
    cx, cy = 410, H - 245

    c.setFillColor(C.text_dim)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(cx, cy + ch + 12, "COMMAND CENTER (/command-center)")

    rounded_rect(c, cx, cy, cw, ch, r=4, fill=HexColor("#1A1A18"), stroke=C.text_muted, stroke_width=0.5)

    # Health score header
    c.setFillColor(C.green)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(cx + 10, cy + ch - 20, "87")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 6)
    c.drawString(cx + 35, cy + ch - 18, "/ 120 Health Score")

    # 4 domain bars
    domains = [
        ("Pipeline", 0.9, C.green),
        ("Coverage", 0.85, C.green),
        ("Bias", 0.75, C.amber),
        ("Content", 0.95, C.green),
    ]
    for i, (name, pct, col) in enumerate(domains):
        dy = cy + ch - 40 - i * 14
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 5)
        c.drawString(cx + 10, dy, name)
        # Bar background
        rounded_rect(c, cx + 55, dy - 1, 100, 8, r=2, fill=C.bg_section)
        # Bar fill
        rounded_rect(c, cx + 55, dy - 1, int(100 * pct), 8, r=2, fill=col)

    # KPI grid (4 cards)
    kpis = [
        ("Last Run", "Completed", C.green),
        ("Articles 24h", "487", C.blue),
        ("Clusters", "1,061", C.teal),
        ("Sources", "419/419", C.green),
    ]
    kpi_w = (cw - 20) / 2
    kpi_h = 28
    for i, (label, val, color) in enumerate(kpis):
        kx = cx + 5 + (i % 2) * (kpi_w + 5)
        ky = cy + ch - 100 - (i // 2) * (kpi_h + 5)
        rounded_rect(c, kx, ky, kpi_w, kpi_h, fill=C.bg_card, stroke=color, stroke_width=0.5)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 4.5)
        c.drawString(kx + 5, ky + 18, label)
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(kx + 5, ky + 5, val)

    # Sparkline placeholder
    c.setFillColor(C.text_muted)
    c.setFont("Helvetica", 5)
    c.drawString(cx + 10, cy + 25, "Bias Distribution (sparkline)")
    c.setStrokeColor(C.amber_dim)
    c.setLineWidth(0.5)
    import random
    random.seed(42)
    pts = [cy + 8 + random.randint(0, 10) for _ in range(12)]
    for i in range(len(pts) - 1):
        c.line(cx + 10 + i * 13, pts[i], cx + 10 + (i + 1) * 13, pts[i + 1])

    # ── PAPER VIEW ──
    pw, ph = 175, 175
    px, py = 605, H - 245

    c.setFillColor(C.text_dim)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(px, py + ph + 12, "PAPER (/paper)")

    rounded_rect(c, px, py, pw, ph, r=4, fill=HexColor("#F5F0E8"), stroke=C.text_muted, stroke_width=0.5)

    # Masthead
    c.setFillColor(HexColor("#1A1A10"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(px + pw / 2, py + ph - 15, "void --news")
    c.setStrokeColor(HexColor("#1A1A10"))
    c.setLineWidth(0.5)
    c.line(px + 10, py + ph - 20, px + pw - 10, py + ph - 20)
    c.line(px + 10, py + ph - 22, px + pw - 10, py + ph - 22)
    c.setFillColor(HexColor("#666650"))
    c.setFont("Helvetica", 5)
    c.drawCentredString(px + pw / 2, py + ph - 30, "Vol. I | March 30, 2026 | World")

    # [F08, F09 fix] Paper columns with proper spacing
    col_w = (pw - 25) / 2
    for col in range(2):
        colx = px + 8 + col * (col_w + 8)
        for row in range(3):
            ry = py + ph - 45 - row * 55
            # Dateline
            c.setFillColor(HexColor("#888870"))
            c.setFont("Helvetica-Bold", 4)
            datelines = [["WASHINGTON", "GENEVA", "BEIJING"], ["CAPE CANAVERAL", "GENEVA", "DC"]]
            c.drawString(colx, ry, datelines[col][row])
            # Headline
            c.setFillColor(HexColor("#1A1A10"))
            c.setFont("Helvetica-Bold", 5.5)
            headlines = [["Fed Holds Rates", "Ukraine Talks", "China GDP 5.4%"],
                        ["SpaceX Orbital", "WHO H5N1 Alert", "AI Copyright"]]
            c.drawString(colx, ry - 10, headlines[col][row])
            # Body lines (dashes)
            c.setFillColor(HexColor("#CCCCBB"))
            c.setFont("Helvetica", 3.5)
            for li in range(4):
                c.drawString(colx, ry - 18 - li * 6, "-" * 18)

    # ── DUPLICATE CONTENT MATRIX (bottom) ──
    mat_x, mat_y = 215, 45
    c.setFillColor(C.dup_high)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(mat_x, mat_y + 125, "DUPLICATE CONTENT MATRIX — What appears where")

    matrix = [
        ("Content", "Desktop\nFeed", "Mobile\nFeed", "Deep\nDive", "Sources", "Cmd\nCenter", "Paper"),
        ("Story headline", "Y", "Y", "Y", "-", "-", "Y"),
        ("Cluster summary", "lead", "hero", "full", "-", "-", "full"),
        ("Bias scores", "sigil", "sigil", "full 4ax", "-", "-", "-"),
        ("TL;DR brief", "skybox", "pill", "-", "-", "-", "-"),
        ("Audio player", "skybox", "pill", "-", "-", "-", "-"),
        ("Source spectrum", "-", "-", "scoring", "full", "-", "-"),
        ("Category filter", "navbar", "bottomnav", "-", "-", "-", "-"),
    ]

    col_w = 55
    row_h = 13
    for ri, row in enumerate(matrix):
        for ci, cell in enumerate(row):
            x = mat_x + ci * col_w
            y = mat_y + 110 - ri * row_h

            if ri == 0:
                c.setFillColor(C.text_muted)
                c.setFont("Helvetica-Bold", 5.5)
            elif cell in ("Y", "full", "full 4ax"):
                c.setFillColor(C.green)
                c.setFont("Helvetica", 5.5)
            elif cell == "-":
                c.setFillColor(HexColor("#444444"))
                c.setFont("Helvetica", 5.5)
            else:
                c.setFillColor(C.dup_medium)
                c.setFont("Helvetica", 5.5)

            display = cell.replace("\n", " ")
            if ci == 0:
                c.drawString(x, y, display)
            else:
                c.drawCentredString(x + col_w / 2, y, display)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 8: COMPONENT MAP
# ══════════════════════════════════════════════════════════════════════════
def page_component_map(c):
    draw_bg(c)
    draw_page_number(c, 8)

    section_title(c, 40, H - 40, "COMPONENT DEPENDENCY MAP — React Tree + Data Sources")

    # Root
    root_y = H - 80
    box_with_label(c, 350, root_y, 130, 28, "App (layout.tsx)", "Root + providers", C.bg_card, C.amber)

    # Pages row
    pages_y = root_y - 55
    pages = [
        ("HomeContent", "/  /us  /india", C.flow_frontend),
        ("PaperContent", "/paper/*", C.flow_frontend),
        ("Sources", "/sources", C.flow_frontend),
        ("CommandCenter", "/command-center", C.flow_frontend),
    ]

    for i, (name, route, color) in enumerate(pages):
        px = 40 + i * 200
        box_with_label(c, px, pages_y, 175, 28, name, route, C.bg_card, color)
        draw_arrow(c, 415, root_y, px + 87, pages_y + 28, C.text_muted, width=1)

    # [F14 fix] HomeContent children with bus-line connector
    hc_y = pages_y - 50
    bus_y = hc_y + 32  # horizontal bus line
    c.setStrokeColor(C.text_muted)
    c.setLineWidth(0.8)
    c.line(47, bus_y, 795, bus_y)

    # Vertical drop from HomeContent
    c.line(127, pages_y, 127, bus_y)

    hc_children = [
        ("NavBar", "2-row header", C.amber_dim),
        ("SkyboxBanner", "TL;DR+Opinion", C.amber),
        ("DesktopFeed", "3-zone layout", C.flow_frontend),
        ("MobileFeed", "Hero+compact", C.flow_frontend),
        ("MobileBottomNav", "3 filter panels", C.teal),
        ("DeepDive", "3-tab modal", C.purple),
        ("Footer", "Logo+products", C.text_muted),
    ]

    child_w = 105
    child_gap = 6
    total_w = len(hc_children) * (child_w + child_gap) - child_gap
    start_x = (W - total_w) / 2

    for i, (name, desc, color) in enumerate(hc_children):
        cx = start_x + i * (child_w + child_gap)
        box_with_label(c, cx, hc_y, child_w, 26, name, desc, C.bg_card, color, font_size=7, sublabel_size=5)
        # Vertical drop from bus
        c.setStrokeColor(C.text_muted)
        c.setLineWidth(0.5)
        c.line(cx + child_w / 2, bus_y, cx + child_w / 2, hc_y + 26)

    # Sub-children for key components
    sub_y = hc_y - 30
    sub_groups = [
        (2, ["LeadStory", "DigestRow", "WireCard"]),  # DesktopFeed
        (3, ["MobileStoryCard", "MobileBriefPill"]),   # MobileFeed
        (5, ["BiasInspector", "Spectrum", "AllSides"]), # DeepDive
    ]
    for parent_idx, subs in sub_groups:
        pcx = start_x + parent_idx * (child_w + child_gap) + child_w / 2
        for j, sub in enumerate(subs):
            sx = pcx - 35 + j * 38
            sw = 36
            rounded_rect(c, sx, sub_y - j * 2, sw, 15, fill=C.bg_section, stroke=C.text_muted, stroke_width=0.4)
            c.setFillColor(C.text_dim)
            c.setFont("Helvetica", 5)
            c.drawCentredString(sx + sw / 2, sub_y - j * 2 + 4, sub)

    # Shared components
    shared_y = sub_y - 50
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, shared_y + 15, "SHARED COMPONENTS (used across multiple parents)")

    shared = [
        ("Sigil", "LeadStory, StoryCard, DigestRow, WireCard, MobileStoryCard, DeepDive footer", C.dup_high),
        ("StoryMeta", "LeadStory, StoryCard, MobileStoryCard (category + time)", C.dup_medium),
        ("ErrorBoundary", "Every page component (graceful error handling)", C.dup_low),
        ("LoadingSkeleton", "HomeContent, PaperContent, Sources (fetch placeholder)", C.dup_low),
        ("LogoWordmark/Full/Icon", "NavBar, Footer, SkyboxBanner, MobileBriefPill", C.dup_medium),
    ]

    for i, (name, parents, color) in enumerate(shared):
        sy2 = shared_y - 5 - i * 16
        c.setFillColor(color)
        c.circle(48, sy2 + 4, 4, fill=1, stroke=0)
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(58, sy2, name)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6)
        c.drawString(170, sy2, parents)

    # Data connections (right side)
    dx = 520
    dy = H - 80
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(dx, dy, "Supabase Data Connections")

    connections = [
        ("HomeContent", "story_clusters (section[], category filter)"),
        ("HomeContent", "daily_briefs (per-edition, latest)"),
        ("DesktopFeed", "story_clusters (sorted by headline_rank)"),
        ("DeepDive", "cluster_articles -> articles -> bias_scores"),
        ("DeepDive", "cluster_bias_summary (view)"),
        ("Sources", "sources (all 419, sorted by lean)"),
        ("CommandCenter", "pipeline_runs + aggregates (14 KPIs)"),
        ("DailyBrief", "daily_briefs.audio_url (Supabase Storage)"),
    ]

    for i, (comp, query) in enumerate(connections):
        cy2 = dy - 22 - i * 20
        c.setFillColor(C.amber)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(dx, cy2 + 5, comp)
        c.setFillColor(C.flow_db)
        c.setFont("Helvetica", 6)
        c.drawString(dx, cy2 - 5, f"  {query}")

    # React hooks
    hy2 = dy - 200
    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(dx, hy2, "Custom Hooks (shared state)")

    hooks = [
        ("useDailyBrief", "Fetch + cache latest brief per edition"),
        ("useStories", "Paginated cluster fetch with filters"),
        ("useAudioPlayer", "Play/pause, progress, seek state"),
        ("useTheme", "Light/dark mode (CSS custom props)"),
        ("useKeyboardNav", "J/K/Enter/Esc/? shortcuts"),
        ("useReducedMotion", "prefers-reduced-motion detection"),
    ]
    for i, (hook, desc) in enumerate(hooks):
        hy3 = hy2 - 18 - i * 15
        c.setFillColor(C.teal)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(dx, hy3, hook)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6)
        c.drawString(dx + 105, hy3, desc)


# ══════════════════════════════════════════════════════════════════════════
# PAGE 9: DATABASE SCHEMA + BIAS ENGINE
# ══════════════════════════════════════════════════════════════════════════
def page_database_bias(c):
    draw_bg(c)
    draw_page_number(c, 9)

    section_title(c, 40, H - 40, "DATABASE SCHEMA + BIAS ENGINE ARCHITECTURE")

    # ── DATABASE TABLES (left half) ──
    tables = [
        ("sources", "419 rows", ["slug (PK)", "name, url, rss_url", "tier, country, type", "political_lean_baseline", "credibility_notes"], C.flow_rss),
        ("articles", "100k+ rows", ["source_id (FK)", "url (unique), title", "summary, full_text (300ch)", "author, published_at", "section, image_url, word_count"], C.blue),
        ("bias_scores", "1:1 article", ["article_id (FK)", "political_lean (0-100)", "sensationalism (0-100)", "opinion_fact (0-100)", "factual_rigor (0-100)", "framing (0-100)", "confidence, rationale JSONB"], C.purple),
        ("story_clusters", "1k+ rows", ["title, summary", "consensus_points, divergence_points", "category, sections text[]", "importance_score, headline_rank", "divergence_score, bias_diversity"], C.teal),
        ("daily_briefs", "per-edition", ["edition, tldr_text", "opinion_text, opinion_lean", "audio_url, audio_duration", "audio_voice, audio_file_size"], C.amber),
    ]

    tx = 40
    ty = H - 80
    table_w = 235

    for ti, (name, size, columns, color) in enumerate(tables):
        th = 16 + len(columns) * 11
        if ty - th < 45:
            tx = 295
            ty = H - 80

        rounded_rect(c, tx, ty - th, table_w, th, fill=C.bg_card, stroke=color, stroke_width=0.8)
        rounded_rect(c, tx, ty - 16, table_w, 16, fill=color)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(tx + 8, ty - 13, name)
        c.setFont("Helvetica", 6)
        c.drawRightString(tx + table_w - 8, ty - 13, size)

        for ci, col in enumerate(columns):
            cyy = ty - 28 - ci * 11
            is_pk = "PK" in col
            is_fk = "FK" in col
            c.setFillColor(C.amber if is_pk else C.blue if is_fk else C.text_dim)
            c.setFont("Helvetica-Bold" if is_pk or is_fk else "Helvetica", 6)
            c.drawString(tx + 12, cyy, col)

        ty -= th + 10

    # Junction tables
    junctions = [
        ("cluster_articles", "cluster_id <-> article_id (junction)"),
        ("article_categories", "article_id <-> category_id (junction)"),
        ("pipeline_runs", "status, counts, timing, errors"),
        ("source_topic_lean", "per-source per-topic EMA (Axis 6)"),
        ("categories", "7 rows: Politics...Culture"),
    ]

    jy = ty - 5
    for ji, (name, desc) in enumerate(junctions):
        rounded_rect(c, tx, jy - 15, table_w, 15, fill=C.bg_section, stroke=C.text_muted, stroke_width=0.5)
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(tx + 8, jy - 12, name)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 5.5)
        c.drawString(tx + 100, jy - 12, desc)
        jy -= 18

    # ── BIAS ENGINE (right half) ── [F02 fix] Shifted left, reduced gap
    bx = 545
    by = H - 80

    c.setFillColor(C.text)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(bx, by, "Bias Engine — 6 Axes")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 7)
    c.drawString(bx, by - 14, "All rule-based NLP | No LLM | $0 cost")

    axes = [
        ("1. Political Lean", "0-100", [
            "90+ left / 90+ right keyword lexicons",
            "Entity sentiment (NER + TextBlob)",
            "Framing phrases detection",
            "Source baseline blending",
            "Length-adaptive + sparsity-weighted",
        ], C.lean_center),
        ("2. Sensationalism", "0-100", [
            "Clickbait pattern matching",
            "Superlative density (word-boundary)",
            "TextBlob extremity score",
            "Partisan attack density (cap 30pt)",
            "Urgency language detection",
        ], C.orange),
        ("3. Opinion vs Report", "0-100", [
            "First/second person pronouns",
            "TextBlob subjectivity score",
            "Attribution density (14 patterns)",
            "Value judgment phrases",
            "Rhetorical question count",
        ], C.purple),
        ("4. Factual Rigor", "0-100", [
            "Named sources (NER + verbs)",
            "Organization citations",
            "Data pattern detection",
            "Direct quotes count",
            "Vague-source penalty",
        ], C.green),
        ("5. Framing", "0-100", [
            "Charged synonym pairs (50+)",
            "Cluster-aware omission detect",
            "Headline-body divergence",
            "Passive voice (cap 30pt)",
            "Tone consistency check",
        ], C.red),
        ("6. Topic Outlet EMA", "adaptive", [
            "Per-topic per-outlet tracking",
            "Alpha 0.3 new / 0.15 established",
            "source_topic_lean table",
            "Rolling average bias profile",
            "Cross-story consistency",
        ], C.teal),
    ]

    col_gap = 142
    aw = 138
    for ai, (name, scale, signals, color) in enumerate(axes):
        row = ai // 2
        col = ai % 2
        axx = bx + col * col_gap
        ay = by - 40 - row * 145
        ah = 130

        # [F02 fix] Verify right edge: bx(545) + 1*142 + 138 = 825 < 841.89
        rounded_rect(c, axx, ay, aw, ah, fill=C.bg_card, stroke=color, stroke_width=0.8)

        rounded_rect(c, axx, ay + ah - 18, aw, 18, r=4, fill=color)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(axx + 5, ay + ah - 15, name)
        c.setFont("Helvetica", 5)
        c.drawRightString(axx + aw - 5, ay + ah - 15, scale)

        for si, sig in enumerate(signals):
            c.setFillColor(C.text_dim)
            c.setFont("Helvetica", 5.5)
            c.drawString(axx + 8, ay + ah - 32 - si * 12, sig)

    # Validation badge [F02 fix] width 280
    vy = by - 485
    rounded_rect(c, bx, vy, 280, 35, fill=HexColor("#1A2A1A"), stroke=C.green, stroke_width=1)
    c.setFillColor(C.green)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(bx + 10, vy + 20, "Validation: 38 articles | 8 cats | 100%")
    c.setFillColor(C.text_dim)
    c.setFont("Helvetica", 7)
    c.drawString(bx + 10, vy + 6, "CI gate: .github/workflows/validate-bias.yml")


# ══════════════════════════════════════════════════════════════════════════
# PAGE 10: OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════
def page_optimization(c):
    draw_bg(c)
    draw_page_number(c, 10)

    section_title(c, 40, H - 40, "OPTIMIZATION OPPORTUNITIES — Duplication, Overlap & Clutter")

    # ── CONTENT DUPLICATION ──
    cx = 40
    cy = H - 78
    c.setFillColor(C.dup_high)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(cx, cy, "Content Duplication")

    dups = [
        ("HIGH", C.dup_high, "SkyboxBanner + MobileBriefPill",
         "Both render TL;DR text + audio player. Desktop banner and mobile pill duplicate content.",
         "Share useDailyBrief hook. Banner should be toggle, not full text render."),
        ("HIGH", C.dup_high, "Gemini Summaries (step 7) + Brief TL;DR (step 9)",
         "Pipeline step 7 and step 9 both summarize same top clusters via separate Gemini calls.",
         "Cascade: brief should build on existing cluster summaries, not re-summarize."),
        ("MED", C.dup_medium, "Sigil + BiasInspector + DeepDiveSpectrum",
         "Three components encode political lean. Sigil (compact), Inspector (4-axis), Spectrum (7-zone).",
         "Intentional progressive disclosure. Data flows from single source."),
        ("MED", C.dup_medium, "Feed Page + Paper Page",
         "Same story data, different layouts (card grid vs newspaper columns).",
         "By design. Verify shared data-fetching hook, no duplicate Supabase queries."),
        ("LOW", C.dup_low, "bias_scores.rationale + gemini_reasoning",
         "Rationale JSONB has both rule-based and Gemini reasoning overlapping.",
         "Merge into single rationale field with source attribution per section."),
    ]

    for i, (severity, color, title, issue, action) in enumerate(dups):
        dy = cy - 22 - i * 55

        badge(c, cx, dy + 35, severity, color)
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(cx + 45, dy + 35, title)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6.5)
        c.drawString(cx + 10, dy + 22, f"Issue: {issue}")
        c.setFillColor(C.green)
        c.setFont("Helvetica", 6.5)
        c.drawString(cx + 10, dy + 10, f"Fix: {action}")

        c.setStrokeColor(C.text_muted)
        c.setLineWidth(0.2)
        c.line(cx, dy + 5, cx + 380, dy + 5)

    # ── SIMPLIFICATION ──
    rx = 440
    ry = H - 78
    c.setFillColor(C.orange)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(rx, ry, "Simplification Opportunities")

    simplifications = [
        ("OpEdPage", "Shelved/disabled. Remove from bundle to reduce size."),
        ("OpinionCard", "Only used in shelved OpEd page. Dead code."),
        ("InstallPrompt", "PWA install — evaluate if needed for static site."),
        ("DivergenceAlerts", "Separate comp — could inline into DeepDive."),
        ("ComparativeView", "Only in DeepDive AllSides tab. Consider inlining."),
        ("KeyboardShortcuts", "Help overlay — low usage vs. complexity."),
    ]

    for i, (comp, note) in enumerate(simplifications):
        sy = ry - 20 - i * 22
        c.setFillColor(C.orange)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(rx, sy + 6, comp)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6.5)
        c.drawString(rx, sy - 5, note)

    # ── METRICS OVERLAP ──
    mx2 = 440
    my2 = ry - 170
    c.setFillColor(C.blue)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(mx2, my2, "Metrics on Multiple Pages")

    metrics = [
        ("Political lean", "Feed(Sigil), DeepDive(Spectrum+Inspector), Sources(Chart)", "3 pg"),
        ("Source count", "Feed(card), DeepDive(header), Paper(dateline)", "3 pg"),
        ("TL;DR brief", "SkyboxBanner, MobileBriefPill, DailyBrief", "3 loc"),
        ("Audio URL", "SkyboxBanner, MobileBriefPill (shared OnAir)", "2 loc"),
        ("Edition filter", "NavBar, MobileBottomNav, DailyBrief, Paper", "4 loc"),
        ("Headline rank", "DesktopFeed sort, Paper sort, CommandCenter", "3 use"),
    ]

    for i, (metric, where, count) in enumerate(metrics):
        yy = my2 - 18 - i * 20
        c.setFillColor(C.text)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(mx2, yy + 5, metric)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6)
        c.drawString(mx2, yy - 5, where)
        cnt_color = C.dup_high if "4" in count else C.dup_medium
        badge(c, mx2 + 310, yy, count, cnt_color)

    # ── BACKEND CONSUMERS ──
    bx2 = 40
    by2 = cy - 305
    c.setFillColor(C.flow_db)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(bx2, by2, "Backend Connection Map")

    conns = [
        ("story_clusters", "Feed, Paper, DeepDive, CommandCenter", "4"),
        ("bias_scores", "DeepDive (full), Feed (via Sigil), Sources", "3"),
        ("daily_briefs", "SkyboxBanner, MobileBriefPill, DailyBrief", "3"),
        ("sources", "Sources page, DeepDiveSpectrum, CommandCenter", "3"),
        ("pipeline_runs", "CommandCenter only", "1"),
        ("source_topic_lean", "No frontend consumer (pipeline internal)", "0"),
        ("article_categories", "NavBar topic counts (via join)", "1"),
    ]

    for i, (table, consumers, count) in enumerate(conns):
        yy = by2 - 16 - i * 16
        c.setFillColor(C.flow_db)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(bx2, yy, table)
        c.setFillColor(C.text_dim)
        c.setFont("Helvetica", 6)
        c.drawString(bx2 + 105, yy, consumers)

        cnt_color = C.green if count in ("0", "1") else C.dup_medium if count == "3" else C.dup_high
        badge(c, bx2 + 330, yy - 2, f"{count} consumers", cnt_color)


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
def main():
    output = "/home/aacrit/projects/void-news/void-news-architecture.pdf"
    pdf = canvas.Canvas(output, pagesize=landscape(A4))
    pdf.setTitle("void --news — Architecture & Wireframe Reference v2")
    pdf.setAuthor("void --news CEO Office")
    pdf.setSubject("System Architecture, Wireframes, Data Flow, Optimization")

    pages = [
        page_cover,
        page_system_architecture,
        page_data_flow,
        page_pipeline_flow,
        page_wireframe_homepage,
        page_wireframe_deepdive,
        page_wireframe_other_pages,
        page_component_map,
        page_database_bias,
        page_optimization,
    ]

    for i, page_fn in enumerate(pages):
        page_fn(pdf)
        if i < len(pages) - 1:
            pdf.showPage()

    pdf.save()
    print(f"PDF generated: {output}")
    print(f"  Pages: {len(pages)}")
    print(f"  Fixes applied: F01-F14 (all 14 UAT issues)")
    print(f"  Wireframes: updated from actual code exploration")


if __name__ == "__main__":
    main()
