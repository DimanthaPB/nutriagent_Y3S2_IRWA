"""
Professional PDF Generator for NutriAgent Week 11 Final Viva Preparation Guide (20 Marks).
Comprehensive, in-depth reference for all 4 team members covering:
1. Technical depth
2. Individual contribution (Members 1, 2, 3, and 4)
3. Understanding of communication protocols
4. Explanation of Responsible AI practices
5. Commercialization and pricing discussion
"""

import os
import pathlib
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic running header and 'Page X of Y' footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "NutriAgent — Final Viva Examination Prep Guide (Week 11 · 20 Marks) | SLIIT IT3041")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_text)
        self.drawString(54, 36, "Confidential — NutriAgent Multi-Agent Nutrition Advisor · University Examination Guide")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * inch - 54, 48)
        self.restoreState()


def build_final_viva_guide(output_filename: str):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#1E3A8A")   # Deep Blue
    secondary_color = colors.HexColor("#0D9488") # Teal
    dark_neutral = colors.HexColor("#0F172A")    # Slate 900
    text_color = colors.HexColor("#334155")      # Slate 700
    accent_green = colors.HexColor("#059669")    # Emerald
    accent_red = colors.HexColor("#DC2626")      # Crimson
    accent_amber = colors.HexColor("#D97706")    # Amber

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SubSectionHeading",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=secondary_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_color,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "BulletCustom",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    q_style = ParagraphStyle(
        "VivaQuestion",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=6,
        spaceAfter=2,
    )

    ans_style = ParagraphStyle(
        "VivaAnswer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=8,
        spaceAfter=6,
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    callout_text = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E293B"),
    )

    elements = []

    # ==================== HEADER BLOCK ====================
    elements.append(Paragraph("NutriAgent — Week 11 Final Viva Prep Guide", title_style))
    elements.append(Paragraph("SLIIT IT3041 Information Retrieval & Web Analytics | 20 Marks Master Preparation Guide", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=0, spaceAfter=12))

    # Viva Rubric Summary Table
    rubric_data = [
        [
            Paragraph("<b>Viva Evaluation Rubric Criteria (20 Marks Total)</b>", ParagraphStyle("Hdr", parent=badge_style, fontSize=9)),
            Paragraph("<b>Core Focus & Key Deliverables</b>", ParagraphStyle("Hdr2", parent=badge_style, fontSize=9)),
        ],
        [
            Paragraph("<b>1. Technical Depth</b>", body_style),
            Paragraph("Architectural soundness, algorithms (spaCy NLP, vector search, Gemini Flash), cryptographic security, and schema robustness.", body_style)
        ],
        [
            Paragraph("<b>2. Individual Contribution</b>", body_style),
            Paragraph("Clear defense of individual agent ownership: Security (Mem 1), Intake (Mem 2), IR (Mem 3), Planning (Mem 4).", body_style)
        ],
        [
            Paragraph("<b>3. Communication Protocols</b>", body_style),
            Paragraph("Chained synchronous HTTP microservices, shared Pydantic contract, distributed UUID4 X-Trace-ID tracing, and HTTP error semantics.", body_style)
        ],
        [
            Paragraph("<b>4. Responsible AI Practices</b>", body_style),
            Paragraph("Grounded retrieval avoiding hallucination, deterministic allergen safety shields, dynamic condition disclaimers, and injection defense.", body_style)
        ],
        [
            Paragraph("<b>5. Commercialization & Pricing</b>", body_style),
            Paragraph("B2C Freemium & B2B Clinic SaaS, token unit economics ($0.0005/plan), cloud container costs, and pricing tiers.", body_style)
        ],
    ]
    t_rubric = Table(rubric_data, colWidths=[2.2 * inch, 4.8 * inch])
    t_rubric.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_rubric)
    elements.append(Spacer(1, 14))

    # ==================== SECTION 1: INDIVIDUAL CONTRIBUTION ====================
    elements.append(Paragraph("1. Individual Contributions & Deep Technical Defense", h1_style))
    elements.append(Paragraph(
        "Each team member owns one autonomous microservice agent running in its own process. In the viva, each member must speak with full technical authority on their own service while understanding how it fits into the synchronous chain.",
        body_style
    ))

    # MEMBER 1
    elements.append(Paragraph("Member 1: Security & Validation Agent (Gateway · Port 8001)", h2_style))
    mem1_points = [
        "<b>Core Role</b>: Acts as the public reverse-proxy gateway and Zero-Trust perimeter. All external requests enter port 8001; internal agents (8002, 8003, 8004) are shielded behind this gateway.",
        "<b>Authentication Architecture</b>: Backed by SQLite (<code>nutriagent.db</code>) using <b>PBKDF2-HMAC-SHA256</b> with unique cryptographic salts (310,000 iterations). Protects against rainbow tables and brute-force attacks. Generates stateless cryptographically signed <b>JWTs (HS256)</b> with 30-minute expiration.",
        "<b>Universal Prompt Injection & Jailbreak Guard</b>: Multi-layered regex engine detecting instruction overrides ('ignore previous instructions'), persona hijacking ('DAN mode', 'act as unrestricted agent'), system prompt leakage, delimiter impersonation, and Unicode de-obfuscation / leetspeak mapping (@ -> a, 0 -> o).",
        "<b>Administrative & Destructive Command Defense</b>: Dedicated filter intercepting destructive commands (<code>delete user</code>, <code>drop database</code>, <code>remove account</code>, <code>truncate table</code>, <code>kill process</code>, <code>rm -rf</code>) with zero false-positives on legitimate nutrition text.",
        "<b>Rate Limiting & Distributed Tracing</b>: SlowAPI client-IP quota enforcement (5 login/min, 10 query/min). Generates and propagates canonical UUID4 <code>X-Trace-ID</code> across all agents without altering JSON payload bodies.",
        "<b>Unified Web Chat Workspace</b>: Built a responsive dark-mode AI Chat client with live multi-agent pipeline animated progress, macro pills, culinary drawers, and audit log inspection modal."
    ]
    for p in mem1_points:
        elements.append(Paragraph(f"• {p}", bullet_style))

    elements.append(Spacer(1, 4))
    elements.append(Paragraph("<b>Likely Viva Questions for Member 1:</b>", q_style))
    elements.append(Paragraph("<b>Q: Why do you validate authentication before checking input text?</b><br/>"
                              "<i>Answer:</i> Evaluating regexes on untrusted, unauthenticated input opens the gateway to Regular Expression Denial of Service (ReDoS) or resource exhaustion. Authenticating first ensures compute-heavy validation runs only for verified users.", ans_style))
    elements.append(Paragraph("<b>Q: How does your system block 'delete user' without blocking 'I want to delete sugar from my diet'?</b><br/>"
                              "<i>Answer:</i> We use context-targeted regexes that specifically pair destructive verbs (delete, drop, remove, purge) with administrative nouns (user, account, table, database, system). It matches <code>\\bdelete\\s+user\\b</code> but allows <code>delete sugar</code> or <code>drop body fat</code>.", ans_style))
    elements.append(Paragraph("<b>Q: Why strip the JWT before forwarding to the Intake Agent?</b><br/>"
                              "<i>Answer:</i> Principle of Least Privilege and Attack Surface Reduction. Downstream microservices are internal and only need the verified user ID and sanitized prompt. Forwarding tokens internally risks token leakage in internal logs or intermediary microservices.", ans_style))

    elements.append(Spacer(1, 8))

    # MEMBER 2
    elements.append(Paragraph("Member 2: Intake & Profile Agent (Port 8002)", h2_style))
    mem2_points = [
        "<b>Core Role</b>: Natural Language Understanding (NLU) service that transforms unstructured, noisy user prompts into a validated Pydantic <code>UserProfile</code> object.",
        "<b>spaCy EntityRuler Pipeline</b>: Employs a custom spaCy EntityRuler pattern matcher over 5 clinical taxonomy categories: <b>Allergies</b> (9 types: peanut, tree nuts, shellfish, dairy, gluten, etc.), <b>Conditions</b> (diabetes, hypertension, celiac, kidney disease, lactose intolerance), <b>Goals</b> (weight loss, muscle gain, maintenance, general health), <b>Diet Types</b> (vegan, vegetarian, keto, pescatarian, halal), and <b>Preferences</b> (high protein, low carb, low sodium, quick meals).",
        "<b>Contextual Windowed Negation Handling</b>: Implements regex lookbehind analysis (<code>_is_negated</code>) to prevent false positives when users deny a condition (e.g. <i>'I have no dairy allergy'</i> or <i>'don't have an allergy to eggs'</i> is correctly discarded).",
        "<b>Calorie Target Numerical Extraction</b>: Regex boundary parser capturing quantitative energy goals (e.g. <i>'about 2200 kcal'</i>, <i>'under 1600 calories'</i>, <i>'no more than 2000 cals'</i>).",
        "<b>SQLite Persistence Store (<code>profiles.sqlite3</code>)</b>: Automatically persists user profiles and merges incremental updates (<code>merge_profiles</code>), allowing returning users to ask one-off queries (<i>'suggest a healthy lunch'</i>) while retaining past medical constraints."
    ]
    for p in mem2_points:
        elements.append(Paragraph(f"• {p}", bullet_style))

    elements.append(Spacer(1, 4))
    elements.append(Paragraph("<b>Likely Viva Questions for Member 2:</b>", q_style))
    elements.append(Paragraph("<b>Q: Why use spaCy EntityRuler instead of a generic LLM prompt to extract profiles?</b><br/>"
                              "<i>Answer:</i> Determinism, latency, and cost. EntityRuler executes in under 2 milliseconds on CPU with 100% deterministic entity extraction, zero hallucination, and no token costs. It guarantees that critical medical allergies are never randomly omitted by non-deterministic LLMs.", ans_style))
    elements.append(Paragraph("<b>Q: How do you handle returning users who change their mind?</b><br/>"
                              "<i>Answer:</i> Our <code>classify_intent()</code> function detects profile update triggers (e.g. 'instead', 'update', 'now'). When detected, <code>merge_profiles()</code> overwrites existing fields (like diet type) while preserving previously declared persistent facts like chronic allergies.", ans_style))

    elements.append(Spacer(1, 10))

    # MEMBER 3
    elements.append(Paragraph("Member 3: Nutrition Information Retrieval (IR) Agent (Port 8003)", h2_style))
    mem3_points = [
        "<b>Core Role</b>: Information Retrieval engine providing grounded nutritional truth. Shields the system from LLM nutritional hallucination by serving real, verified food records.",
        "<b>Dense Vector Embeddings</b>: Encodes user food queries into 384-dimensional dense semantic vector space using the <code>sentence-transformers</code> model (<code>all-MiniLM-L6-v2</code>).",
        "<b>ChromaDB Vector Store</b>: Indexes USDA FoodData Central and curated whole-food recipe datasets (<code>foods.csv</code>, <code>epi_r.csv</code>) in a persistent ChromaDB instance.",
        "<b>Deterministic Hard-Filtering Safety Layer</b>: Applies strict boolean set-exclusion filters for all user allergies (e.g., completely dropping any food containing peanut, dairy, or shellfish ingredients) regardless of how high its vector similarity score is.",
        "<b>Nutritional Fact Grounding</b>: Attaches verified calories, protein (g), carbohydrates (g), fat (g), and source attribution to every retrieved food item sent to the Planning Agent."
    ]
    for p in mem3_points:
        elements.append(Paragraph(f"• {p}", bullet_style))

    elements.append(Spacer(1, 4))
    elements.append(Paragraph("<b>Likely Viva Questions for Member 3:</b>", q_style))
    elements.append(Paragraph("<b>Q: Why do vector similarity search and then apply hard filtering, instead of just filtering?</b><br/>"
                              "<i>Answer:</i> Vector search finds semantically relevant items that match user tastes and goals (e.g. 'comfort food' or 'high protein dinner'). However, vector distance is probabilistic. To ensure 100% life-critical patient safety, deterministic hard filtering must strictly eliminate allergens after retrieval.", ans_style))
    elements.append(Paragraph("<b>Q: What happens if the query matches no safe foods in the database?</b><br/>"
                              "<i>Answer:</i> The IR Agent returns an empty items list <code>[]</code>. Downstream, the Planning Agent detects this and gracefully explains that no foods safely satisfy both the calorie targets and strict allergen constraints, preventing dangerous fallbacks.", ans_style))

    elements.append(Spacer(1, 10))

    # MEMBER 4
    elements.append(Paragraph("Member 4: Meal Planning & Reasoning Agent (Port 8004)", h2_style))
    mem4_points = [
        "<b>Core Role</b>: Reasoning engine that transforms retrieved grounded foods and user clinical constraints into an empathetic, actionable, and explainable meal plan.",
        "<b>Google Gemini Generative AI Integration</b>: Integrates Google's <code>google-genai</code> SDK utilizing Gemini Flash models (<code>gemini-2.5-flash</code>, <code>gemini-2.0-flash</code>) with strict schema validation against the Pydantic <code>MealPlan</code> schema.",
        "<b>Strict Grounding Constraints</b>: System prompt strictly forbids the model from inventing foods, modifying calorie numbers, or adding unretrieved ingredients. It reasons ONLY over the provided <code>retrieved_items</code>.",
        "<b>Culinary Enrichment & Recipes</b>: Generates whole-food ingredient breakdowns and actionable Chef's <code>prep_tip</code> for cooking, seasoning, and meal-prep.",
        "<b>Sharp Allergen Safety Shield</b>: Generates explicit <code>allergen_safety_note</code> certifying that the meal is 100% free of the user's declared allergies, providing peace of mind.",
        "<b>Dynamic Condition-Tailored Disclaimers</b>: Replaces static disclaimers with <code>generate_dynamic_disclaimer()</code>, generating targeted medical guidance (e.g., sodium restriction for hypertension, glycemic indexing for diabetes, cross-contamination warnings for celiac disease).",
        "<b>Synchronized Resilient Fallback Engine</b>: Deterministic rule-based fallback planner that operates with full recipe tips, macros, and disclaimers if offline or when API quotas are exhausted."
    ]
    for p in mem4_points:
        elements.append(Paragraph(f"• {p}", bullet_style))

    elements.append(Spacer(1, 4))
    elements.append(Paragraph("<b>Likely Viva Questions for Member 4:</b>", q_style))
    elements.append(Paragraph("<b>Q: How do you prevent Gemini from hallucinating inaccurate calories?</b><br/>"
                              "<i>Answer:</i> Our prompt explicitly passes retrieved nutrition facts as immutable data and instructs the model to copy calories and macros verbatim. Furthermore, our post-processing validator cross-checks the LLM output against the original retrieved items before sending it back.", ans_style))
    elements.append(Paragraph("<b>Q: Why do you have dynamic disclaimers instead of a single static disclaimer?</b><br/>"
                              "<i>Answer:</i> Responsible AI and patient-centric safety. A diabetic patient requires warnings regarding carbohydrate monitoring and insulin therapy, whereas a hypertension patient needs low-sodium advice. Tailoring disclaimers provides medically accurate context without giving illegal medical diagnoses.", ans_style))

    elements.append(PageBreak())

    # ==================== SECTION 2: COMMUNICATION PROTOCOLS ====================
    elements.append(Paragraph("2. Understanding of Communication Protocols (Rubric Item 3)", h1_style))
    elements.append(Paragraph(
        "NutriAgent adopts a <b>Synchronous Chained HTTP Microservices Pattern</b> over RESTful JSON APIs. Below are the key architectural decisions you must defend in the viva:",
        body_style
    ))

    comm_table_data = [
        [
            Paragraph("<b>Protocol Aspect</b>", ParagraphStyle("H1", parent=badge_style)),
            Paragraph("<b>NutriAgent Implementation</b>", ParagraphStyle("H2", parent=badge_style)),
            Paragraph("<b>Architectural Justification</b>", ParagraphStyle("H3", parent=badge_style)),
        ],
        [
            Paragraph("<b>Communication Style</b>", body_style),
            Paragraph("Synchronous chained HTTP (Client -> Sec -> Intake -> IR -> Planning -> Return)", body_style),
            Paragraph("The user is waiting in real-time in the Chat UI. Synchronous chaining provides immediate feedback without the operational overhead of message queues.", body_style)
        ],
        [
            Paragraph("<b>Shared Schema Contract</b>", body_style),
            Paragraph("<code>shared/schemas.py</code> imported by all 4 agents", body_style),
            Paragraph("Single Source of Truth. Eliminates schema drift between independently developed microservices.", body_style)
        ],
        [
            Paragraph("<b>Distributed Tracing</b>", body_style),
            Paragraph("HTTP Header: <code>X-Trace-ID</code> (canonical UUID4)", body_style),
            Paragraph("Enables end-to-end request correlation across all 4 independent logs without modifying JSON payload schemas.", body_style)
        ],
        [
            Paragraph("<b>Security Boundary</b>", body_style),
            Paragraph("Gateway terminates auth; forwards plaintext <code>user_id</code> and <code>raw_text</code>", body_style),
            Paragraph("Downstream agents remain stateless and decoupled from user credential management.", body_style)
        ],
        [
            Paragraph("<b>Error Code Semantics</b>", body_style),
            Paragraph("400 (Bad input), 401 (Auth fail), 403 (Mismatch), 422 (Schema err), 429 (Rate limit), 502 (Downstream fail), 504 (Timeout)", body_style),
            Paragraph("Standardized HTTP status codes allow frontends and gateways to handle network, security, and application errors deterministically.", body_style)
        ],
    ]
    t_comm = Table(comm_table_data, colWidths=[1.8 * inch, 2.5 * inch, 2.7 * inch])
    t_comm.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_comm)

    elements.append(Spacer(1, 12))

    # ==================== SECTION 3: RESPONSIBLE AI PRACTICES ====================
    elements.append(Paragraph("3. Explanation of Responsible AI Practices (Rubric Item 4)", h1_style))
    elements.append(Paragraph(
        "Responsible AI is a primary evaluation pillar for health-related AI applications. NutriAgent embeds safety into every microservice layer:",
        body_style
    ))

    rai_points = [
        "<b>1. Hallucination Prevention via Grounded Retrieval</b>: Standard LLMs hallucinate nutritional numbers. NutriAgent forces the Planning Agent to recommend <i>only</i> items retrieved and verified by the Nutrition IR Agent from real datasets (USDA). The LLM's role is restricted to reasoning and culinary explanation, not data creation.",
        "<b>2. Life-Critical Allergen Safety Guardrails</b>: Allergies can be fatal (anaphylaxis). We do not trust probabilistic LLM reasoning to filter out allergens. Instead, the IR Agent executes deterministic boolean filtering, and the Planning Agent provides an explicit <code>allergen_safety_note</code> certifying zero cross-contamination risk.",
        "<b>3. Ethical & Legal Boundaries (Dynamic Medical Disclaimers)</b>: NutriAgent is an AI advisor, not a licensed medical doctor. Every recommendation concludes with a tailored health disclaimer explaining that advice does not supersede professional medical supervision, customized to specific chronic conditions (diabetes, hypertension, celiac).",
        "<b>4. Adversarial Attack & Jailbreak Resistance</b>: The Security Gateway filters prompt injection, persona hijackings (DAN mode), instruction overrides, and administrative command attacks (<code>delete user</code>), preventing the model from generating unsafe or toxic advice.",
        "<b>5. Privacy & Data Minimization</b>: Passwords are protected using salted PBKDF2 hashing. Structured request logs redact PII, tokens, and health queries. Only UUID4 trace IDs and latency metrics are recorded."
    ]
    for p in rai_points:
        elements.append(Paragraph(f"• {p}", bullet_style))

    elements.append(Spacer(1, 12))

    # ==================== SECTION 4: COMMERCIALIZATION & PRICING ====================
    elements.append(Paragraph("4. Commercialization & Pricing Discussion (Rubric Item 5)", h1_style))
    elements.append(Paragraph(
        "In the viva, examiners evaluate whether the team understands real-world viability, cloud infrastructure costs, API unit economics, and monetization strategies.",
        body_style
    ))

    # Unit economics table
    econ_data = [
        [
            Paragraph("<b>Cost Category</b>", ParagraphStyle("E1", parent=badge_style)),
            Paragraph("<b>Unit / Monthly Cost</b>", ParagraphStyle("E2", parent=badge_style)),
            Paragraph("<b>Estimated Impact on Margin</b>", ParagraphStyle("E3", parent=badge_style)),
        ],
        [
            Paragraph("<b>Gemini 2.0 Flash API</b>", body_style),
            Paragraph("$0.10 / 1M input tokens<br/>$0.40 / 1M output tokens", body_style),
            Paragraph("<b>< $0.0005 per meal plan generated!</b> Incredibly high gross margin (>95%).", body_style)
        ],
        [
            Paragraph("<b>Microservice Hosting</b>", body_style),
            Paragraph("Containerized on AWS ECS Fargate or Google Cloud Run (~$35/month)", body_style),
            Paragraph("Scales to zero when idle; auto-scales up during peak meal planning hours.", body_style)
        ],
        [
            Paragraph("<b>ChromaDB Vector Store</b>", body_style),
            Paragraph("Chroma Cloud or persistent AWS EBS volume (~$15/month)", body_style),
            Paragraph("Extremely cost-effective for whole-food catalog embeddings.", body_style)
        ],
    ]
    t_econ = Table(econ_data, colWidths=[2.0 * inch, 2.4 * inch, 2.6 * inch])
    t_econ.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), secondary_color),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_econ)
    elements.append(Spacer(1, 10))

    # Pricing Strategy Table
    pricing_data = [
        [
            Paragraph("<b>Tier</b>", ParagraphStyle("P1", parent=badge_style)),
            Paragraph("<b>Price</b>", ParagraphStyle("P2", parent=badge_style)),
            Paragraph("<b>Target Audience & Included Features</b>", ParagraphStyle("P3", parent=badge_style)),
        ],
        [
            Paragraph("<b>Free Tier</b>", body_style),
            Paragraph("$0 / month", body_style),
            Paragraph("3 meal plans / day, basic calorie and allergen filtering. Acts as consumer acquisition funnel.", body_style)
        ],
        [
            Paragraph("<b>Pro Tier (B2C)</b>", body_style),
            Paragraph("<b>$9.99 / mo</b><br/>or $79 / yr", body_style),
            Paragraph("Unlimited meal plans, Chef's recipe preparation tips, macro breakdown pills, family allergen profiles, and exportable grocery lists.", body_style)
        ],
        [
            Paragraph("<b>Clinic / Dietitian Tier (B2B)</b>", body_style),
            Paragraph("<b>$99.00 / mo</b><br/>per practitioner", body_style),
            Paragraph("Dietitian dashboard, patient EHR integration, custom clinical nutrition constraints, audit logs, and branded PDF exports for clinic patients.", body_style)
        ],
    ]
    t_pricing = Table(pricing_data, colWidths=[1.8 * inch, 1.6 * inch, 3.6 * inch])
    t_pricing.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_pricing)

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Viva Tip for Commercialization:</b>", q_style))
    elements.append(Paragraph(
        "When asked <i>'How does NutriAgent beat MyFitnessPal or generic ChatGPT?'</i>, answer: <br/>"
        "1. <b>Safety vs. Hallucination</b>: ChatGPT hallucinates nutrition numbers and has caused allergic reactions; NutriAgent grounds all numbers in verified USDA datasets.<br/>"
        "2. <b>Personalized Clinical Tailoring</b>: MyFitnessPal is a manual calorie logger; NutriAgent is an active multi-agent AI advisor that creates actionable, chef-guided meal plans tailored to specific health conditions.",
        ans_style
    ))

    # Build the document
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"Successfully generated Viva Preparation Guide PDF: {output_filename}")


if __name__ == "__main__":
    output_pdf = "NutriAgent_Final_Viva_Comprehensive_Guide.pdf"
    build_final_viva_guide(output_pdf)
