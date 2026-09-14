"""
PDF Generator for NutriAgent Mid-Evaluation Group Discussion Guide
Provides clear, structured, high-scoring answers to all 6 evaluation criteria.
"""

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
    """Two-pass canvas for dynamic header and 'Page X of Y' footer."""
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
        self.setFont("Helvetica", 8.5)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "NutriAgent — Mid-Evaluation Q&A Discussion Guide | IT3041 SLIIT")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_text)
        self.drawString(54, 36, "Group Assignment Mid-Evaluation Preparation Guide (20 Marks)")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 8.5 * inch - 54, 48)
        self.restoreState()


def generate_mid_eval_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=48,
        rightMargin=48,
        topMargin=50,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()

    # Color Palette
    PRIMARY = colors.HexColor("#0F172A")      # Slate 900
    ACCENT = colors.HexColor("#1D4ED8")       # Blue 700
    EMERALD = colors.HexColor("#047857")      # Emerald 700
    AMBER = colors.HexColor("#B45309")        # Amber 700
    TEXT_MAIN = colors.HexColor("#1E293B")    # Slate 800
    TEXT_MUTED = colors.HexColor("#475569")   # Slate 600
    BG_CARD = colors.HexColor("#F8FAFC")      # Slate 50
    BORDER = colors.HexColor("#E2E8F0")       # Slate 200

    # Custom Typography
    title_style = ParagraphStyle(
        "EvalTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        alignment=0,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "EvalSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=ACCENT,
        spaceAfter=10,
    )

    badge_style = ParagraphStyle(
        "EvalBadge",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=TEXT_MUTED,
        spaceAfter=12,
    )

    q_title_style = ParagraphStyle(
        "QTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )

    subheading_style = ParagraphStyle(
        "SubHeading",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=ACCENT,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "EvalBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=12.8,
        textColor=TEXT_MAIN,
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "EvalBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.6,
        leading=12.4,
        textColor=TEXT_MAIN,
        leftIndent=12,
        spaceAfter=2.5,
    )

    highlight_style = ParagraphStyle(
        "EvalHighlight",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.8,
        leading=12.5,
        textColor=EMERALD,
    )

    story = []

    # Title Banner
    story.append(Paragraph("NutriAgent: Mid-Evaluation Group Discussion Guide", title_style))
    story.append(Paragraph("Structured Answers & Talking Points for the 15-Minute Panel Discussion (20 Marks)", subtitle_style))
    story.append(Paragraph("<b>Course:</b> IT3041 Information Retrieval & Web Analytics | <b>Institution:</b> SLIIT | <b>Format:</b> 15-Min Group Discussion", badge_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=10))

    # Introduction Box
    intro_box = [[
        Paragraph(
            "<b>Evaluation Goal:</b> The panel evaluates conceptual clarity, system architecture, realistic planning, Responsible AI, and business value. Use this document to align all 4 group members with consistent, polished answers.",
            body_style
        )
    ]]
    t_intro = Table(intro_box, colWidths=[7.2 * inch])
    t_intro.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#BFDBFE")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_intro)
    story.append(Spacer(1, 8))

    # =========================================================================
    # QUESTION 1
    # =========================================================================
    story.append(Paragraph("1. Why You Selected the Domain & Problem Statement", q_title_style))
    story.append(Paragraph("<b>Real-World Problem:</b>", subheading_style))
    story.append(Paragraph("• <b>Generic & Unsafe Online Advice:</b> Millions of people seek dietary advice online, but general search engines return generic or contradictory advice that ignores personal health restrictions.", bullet_style))
    story.append(Paragraph("• <b>Fatal Risks with Food Allergies:</b> Individuals with severe allergies (peanuts, shellfish, gluten) or conditions (diabetes, hypertension) risk severe harm if recommendations are not strictly filtered.", bullet_style))
    story.append(Paragraph("• <b>LLM Hallucination Problem:</b> Standard Large Language Models (e.g., ChatGPT) invent fake calorie counts and nutritional macros because they are trained to generate plausible text, not retrieve factual nutrition data.", bullet_style))
    story.append(Paragraph("• <b>High Cost of Professional Nutritionists:</b> Personalized consultation with clinical dietitians is unaffordable or inaccessible for many everyday individuals.", bullet_style))

    story.append(Paragraph("<b>Who Experiences This Problem?</b>", subheading_style))
    story.append(Paragraph("• Individuals with food allergies and chronic health conditions (celiac, diabetes, lactose intolerance).", bullet_style))
    story.append(Paragraph("• Fitness enthusiasts, athletes, and bodybuilders needing exact macronutrient targets (protein, carbs, fat).", bullet_style))
    story.append(Paragraph("• Busy professionals and families seeking quick, tailored, and healthy weekly meal plans.", bullet_style))

    story.append(Paragraph("<b>Why is Agentic AI Suitable for Addressing It?</b>", subheading_style))
    story.append(Paragraph("• A monolithic single AI model cannot handle security, NLP extraction, factual database retrieval, and constrained reasoning without failing or hallucinating.", bullet_style))
    story.append(Paragraph("• <b>Agentic Separation of Concerns:</b> By delegating specialized tasks to independent agents (e.g. deterministic hard-filtering in the IR Agent and explainable reasoning in the Planning Agent), we guarantee safety and factual accuracy.", bullet_style))
    story.append(Spacer(1, 6))

    # =========================================================================
    # QUESTION 2
    # =========================================================================
    story.append(Paragraph("2. Proposed System (What We Are Developing)", q_title_style))
    story.append(Paragraph("<b>System Identity:</b> <b>NutriAgent</b> — A Multi-Agent AI Nutrition Advisory Microservice System.", subheading_style))
    story.append(Paragraph("• <b>What it Does:</b> Accepts natural language input from a user (e.g., <i>'I want to build muscle, I'm allergic to peanuts, and I prefer vegetarian food'</i>), extracts dietary requirements, retrieves factual food records from official nutrition databases (USDA), and constructs an explainable, fact-checked meal plan.", bullet_style))
    story.append(Paragraph("• <b>Core Value Proposition:</b>", subheading_style))
    story.append(Paragraph("  1. <b>Zero Hallucinated Numbers:</b> Every calorie and macro number comes from verified USDA food data.", bullet_style))
    story.append(Paragraph("  2. <b>Guaranteed Safety:</b> Strict deterministic allergy filtering ensures allergen-containing items never reach the user.", bullet_style))
    story.append(Paragraph("  3. <b>Explainability:</b> Every meal recommendation includes a transparent 'reason' citing user-specific goals and preferences.", bullet_style))
    story.append(Spacer(1, 6))

    # =========================================================================
    # QUESTION 3
    # =========================================================================
    story.append(Paragraph("3. Agents and Their Roles (Architecture & Communication)", q_title_style))
    story.append(Paragraph("Our system contains <b>4 independent microservices</b> connected in a synchronous HTTP chained architecture with a shared Pydantic JSON contract (<code>shared/schemas.py</code>):", body_style))

    # Agent Table
    agent_table_data = [
        [
            Paragraph("<b>Agent Name & Port</b>", body_style),
            Paragraph("<b>Why It Is Necessary</b>", body_style),
            Paragraph("<b>What It Does (Core Responsibilities)</b>", body_style)
        ],
        [
            Paragraph("<b>1. Security & Validation Agent</b><br/>(Port 8001)", body_style),
            Paragraph("Protects the system from malicious attacks and validates input before processing.", body_style),
            Paragraph("• System front door / API gateway.<br/>• JWT authentication & authorization.<br/>• Prompt injection defense & regex sanitization.<br/>• Rate limiting (slowapi) & trace-ID audit logging.", body_style)
        ],
        [
            Paragraph("<b>2. Intake & Profile Agent</b><br/>(Port 8002)", body_style),
            Paragraph("Converts unstructured human conversation into machine-readable user profiles.", body_style),
            Paragraph("• Natural Language Processing (NER) extraction.<br/>• Identifies user goals, allergies, medical conditions, and diet types.<br/>• Produces validated <code>UserProfile</code> JSON.<br/>• Coordinates downstream IR and Planning agents.", body_style)
        ],
        [
            Paragraph("<b>3. Nutrition IR Agent</b><br/>(Port 8003)", body_style),
            Paragraph("Acts as the 'Ground Truth' factual layer to prevent LLM hallucinations.", body_style),
            Paragraph("• Dense vector semantic search (Sentence-Transformers <code>all-MiniLM-L6-v2</code> + ChromaDB).<br/>• Indexes USDA Foundation Foods (1,178 items).<br/>• Deterministic allergy & dietary hard-filtering.<br/>• Returns factual <code>FoodItem</code> objects with real macros.", body_style)
        ],
        [
            Paragraph("<b>4. Meal Planning Agent</b><br/>(Port 8004)", body_style),
            Paragraph("Synthesizes retrieved ingredients into practical, explainable meal plans.", body_style),
            Paragraph("• LLM reasoning layer (Claude / OpenAI SDK).<br/>• Prompt constrained strictly to retrieved items.<br/>• Generates transparent 'reason' strings per meal.<br/>• Outputs validated <code>MealPlan</code> structure.", body_style)
        ]
    ]

    t_agents = Table(agent_table_data, colWidths=[1.8 * inch, 2.0 * inch, 3.4 * inch])
    t_agents.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_CARD),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t_agents)
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>How Agents Interact:</b> Synchronous HTTP chain: Client ──► Security (8001) ──► Intake (8002) ──► calls IR (8003), then calls Planning (8004) ──► Response flows back: Planning ──► Intake ──► Security ──► Client.", body_style))
    story.append(Spacer(1, 6))

    # =========================================================================
    # QUESTION 4
    # =========================================================================
    story.append(Paragraph("4. Technical Implementation Plan", q_title_style))
    story.append(Paragraph("We have a clean, modular, and realistic technology stack:", body_style))
    story.append(Paragraph("• <b>Microservices Framework:</b> FastAPI (Python) running on independent ports (8001–8004) for lightweight, high-performance async HTTP communication.", bullet_style))
    story.append(Paragraph("• <b>Natural Language Processing (Intake):</b> spaCy Named Entity Recognition (NER) and regex entity extractors to extract allergies, goals, and conditions into Pydantic models.", bullet_style))
    story.append(Paragraph("• <b>Information Retrieval (IR):</b> Embedded <code>chromadb</code> vector database with <code>sentence-transformers</code> (<code>all-MiniLM-L6-v2</code>) for dense semantic retrieval over USDA datasets, paired with deterministic Python boolean filters for safety.", bullet_style))
    story.append(Paragraph("• <b>Generative AI / LLM Reasoning (Planning):</b> OpenAI / Anthropic Claude API with strict temperature control and prompt containment (forcing the model to only recommend items retrieved by the IR Agent).", bullet_style))
    story.append(Paragraph("• <b>Security & Cryptography:</b> <code>pyjwt</code> for token validation, <code>cryptography.fernet</code> for field-level health data encryption, and <code>slowapi</code> for DDoS/rate limiting.", bullet_style))
    story.append(Spacer(1, 6))

    # =========================================================================
    # QUESTION 5
    # =========================================================================
    story.append(Paragraph("5. Responsible AI (RAI) Plan", q_title_style))
    story.append(Paragraph("Addressing ethical and safety risks is central to NutriAgent's design:", body_style))

    rai_data = [
        [
            Paragraph("<b>Responsible AI Pillar</b>", body_style),
            Paragraph("<b>Potential Risk in Nutrition Domain</b>", body_style),
            Paragraph("<b>NutriAgent Mitigation Strategy</b>", body_style)
        ],
        [
            Paragraph("<b>Explainability & Transparency</b>", body_style),
            Paragraph("Black-box AI recommendations where users don't know why a food was chosen.", body_style),
            Paragraph("Every meal includes an explicit <code>reason</code> string tied to the user's profile and cites the factual data source (e.g. <code>usda_fooddata_central</code>).", body_style)
        ],
        [
            Paragraph("<b>Safety & Harm Prevention</b>", body_style),
            Paragraph("Severe allergic reactions or dangerous advice for medical conditions.", body_style),
            Paragraph("Deterministic post-filtering guarantees allergens are excluded in code before reaching the LLM. Mandatory medical disclaimer: <i>'AI guidance, not medical advice.'</i>", body_style)
        ],
        [
            Paragraph("<b>Privacy & Data Protection</b>", body_style),
            Paragraph("Exposure of sensitive health conditions, eating habits, and personal goals.", body_style),
            Paragraph("Symmetric encryption (Fernet) for stored health data, stateless request processing, and trace-ID logging without logging raw PII.", body_style)
        ],
        [
            Paragraph("<b>Fairness & Inclusivity</b>", body_style),
            Paragraph("Biased food recommendations favoring only Western diets.", body_style),
            Paragraph("Dataset includes diverse international ingredients, vegetarian, vegan, and multicultural food options.", body_style)
        ]
    ]

    t_rai = Table(rai_data, colWidths=[1.6 * inch, 2.6 * inch, 3.0 * inch])
    t_rai.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_CARD),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t_rai)
    story.append(Spacer(1, 6))

    # =========================================================================
    # QUESTION 6
    # =========================================================================
    story.append(Paragraph("6. Commercialization & Business Plan", q_title_style))
    story.append(Paragraph("<b>Target Users & Market Segments:</b>", subheading_style))
    story.append(Paragraph("• <b>B2C Consumers:</b> Health-conscious individuals, fitness enthusiasts, bodybuilders, and people managing dietary restrictions.", bullet_style))
    story.append(Paragraph("• <b>B2B Professionals:</b> Dietitians, personal trainers, gym chains, and corporate wellness platforms needing automated meal plan creation.", bullet_style))

    story.append(Paragraph("<b>Value Proposition:</b>", subheading_style))
    story.append(Paragraph("• Reduces meal planning time from hours to seconds.", bullet_style))
    story.append(Paragraph("• Eliminates nutritional calculation errors with certified government nutrition databases.", bullet_style))
    story.append(Paragraph("• Provides enterprise-grade allergy safety and privacy compliance at a fraction of manual consultation costs.", bullet_style))

    story.append(Paragraph("<b>Revenue & Pricing Models:</b>", subheading_style))
    story.append(Paragraph("1. <b>B2C Freemium:</b> Free basic daily meal plan; <b>$9.99/month Pro</b> for weekly grocery list generation, micronutrient tracking, and smart recipe substitutions.", bullet_style))
    story.append(Paragraph("2. <b>B2B SaaS Subscription:</b> <b>$49–$199/month</b> per clinic/gym for client management dashboard and branded white-label meal plan exports.", bullet_style))
    story.append(Paragraph("3. <b>B2B API Licensing:</b> Usage-based API pricing ($0.02 per request) for third-party fitness and healthcare mobile apps.", bullet_style))

    story.append(Paragraph("<b>Deployment & Market Introduction:</b>", subheading_style))
    story.append(Paragraph("• Phase 1: Deploy microservices in lightweight Docker containers on cloud platforms (AWS / Render).", bullet_style))
    story.append(Paragraph("• Phase 2: Launch a mobile/web frontend (React / Flutter) with direct integration into wearable health APIs (Apple Health, Fitbit).", bullet_style))
    story.append(Spacer(1, 8))

    # Summary Footer Banner
    summary_box = [[
        Paragraph(
            "<b>Key Takeaway for the 15-Min Evaluation:</b> Remember that <b>NutriAgent</b> stands out because it solves the <i>LLM Hallucination & Safety problem</i> using an <b>Agentic architecture</b> with <b>Information Retrieval ground-truth data</b>. Emphasize how your microservices collaborate cleanly!",
            body_style
        )
    ]]
    t_summary = Table(summary_box, colWidths=[7.2 * inch])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ECFDF5")),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#A7F3D0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_summary)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Mid Evaluation PDF successfully generated at: {output_path}")


if __name__ == "__main__":
    base_dir = pathlib.Path(__file__).resolve().parent
    out_file = str(base_dir / "NutriAgent_Mid_Evaluation_Prep_Guide.pdf")
    generate_mid_eval_pdf(out_file)
