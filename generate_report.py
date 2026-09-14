"""
PDF Report Generator for NutriAgent Project
Based on AGENTS.md, README.md, and System Architecture Documentation.
Uses ReportLab to build a professional, styled academic/technical report.
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
    """Two-pass canvas to dynamically add 'Page X of Y' and running header/footer."""
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
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))

        # Skip header on first page
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "NutriAgent — Multi-Agent AI Nutrition Advisory System | Project Report")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.75)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer on all pages
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, page_text)
        self.drawString(54, 36, "SLIIT — IT3041 Information Retrieval & Web Analytics")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(54, 48, 8.5 * inch - 54, 48)
        self.restoreState()


def generate_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#0F172A")      # Slate 900
    BRAND = colors.HexColor("#2563EB")        # Blue 600
    SECONDARY = colors.HexColor("#0D9488")    # Teal 600
    TEXT_MAIN = colors.HexColor("#1E293B")    # Slate 800
    TEXT_MUTED = colors.HexColor("#64748B")   # Slate 500
    BG_LIGHT = colors.HexColor("#F8FAFC")     # Slate 50
    BG_CARD = colors.HexColor("#F1F5F9")      # Slate 100
    BORDER = colors.HexColor("#CBD5E1")       # Slate 300

    # Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        alignment=0,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=BRAND,
        spaceAfter=15,
    )

    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=TEXT_MUTED,
        spaceAfter=18,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=BRAND,
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_MAIN,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_MAIN,
        leftIndent=15,
        spaceAfter=3,
    )

    callout_style = ParagraphStyle(
        "Callout_Text",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=PRIMARY,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("NutriAgent: Multi-Agent AI Nutrition Advisor", title_style))
    story.append(Paragraph("System Architecture, Agent Specifications, Shared Contracts & Implementation Roadmap", subtitle_style))
    story.append(Paragraph("<b>Course:</b> IT3041 — Information Retrieval & Web Analytics | <b>Institution:</b> SLIIT | <b>Architecture:</b> 4-Agent Microservice Pipeline", meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND, spaceAfter=14))

    # Section 1: Executive Summary
    story.append(Paragraph("1. Executive Summary & Purpose", h1_style))
    story.append(Paragraph(
        "<b>NutriAgent</b> is a multi-agent artificial intelligence nutrition advisory system designed to convert messy, free-text dietary requirements, allergies, medical conditions, and wellness goals into personalized, explainable, and factually grounded meal plans. Unlike conventional black-box LLM systems that frequently hallucinate nutritional values and calorie counts, NutriAgent grounds all reasoning in verifiable nutrition datasets retrieved through dense semantic vector search.",
        body_style
    ))
    story.append(Paragraph(
        "The system is decomposed into <b>four independent microservices (agents)</b>, each assigned to a team member and communicating over synchronous HTTP with strict JSON schema contracts. There is no central orchestrator or message broker; communication follows a direct chained request-response flow.",
        body_style
    ))

    # Section 2: Architecture & Workflow
    story.append(Paragraph("2. System Architecture & Request-Response Pipeline", h1_style))
    story.append(Paragraph(
        "The architecture follows a synchronous chained pipeline designed for modularity, testability, and clear separation of concerns:",
        body_style
    ))

    # Architecture Flow Table
    flow_data = [
        [
            Paragraph("<b>Stage</b>", body_style),
            Paragraph("<b>Agent & Port</b>", body_style),
            Paragraph("<b>Role & Responsibilities</b>", body_style),
            Paragraph("<b>Data Input / Output</b>", body_style)
        ],
        [
            Paragraph("<b>1. Gateway</b>", body_style),
            Paragraph("<b>Security Agent</b><br/>Port 8001", body_style),
            Paragraph("System front-door. Handles authentication, prompt injection detection, input sanitization, rate limiting, and structured audit logging.", body_style),
            Paragraph("<b>In:</b> SecurityRequest<br/><b>Out:</b> MealPlan (forwarded)", body_style)
        ],
        [
            Paragraph("<b>2. Extraction</b>", body_style),
            Paragraph("<b>Intake Agent</b><br/>Port 8002", body_style),
            Paragraph("Natural Language Processing engine. Extracts structured entities (goals, allergies, conditions, diet types) into a validated UserProfile.", body_style),
            Paragraph("<b>In:</b> IntakeRequest<br/><b>Out:</b> UserProfile, coordinates downstream", body_style)
        ],
        [
            Paragraph("<b>3. Retrieval</b>", body_style),
            Paragraph("<b>Nutrition IR Agent</b><br/>Port 8003", body_style),
            Paragraph("Ground truth knowledge layer. Performs dense vector search (ChromaDB + Sentence-Transformers) on USDA food data and applies strict allergen/diet safety filters.", body_style),
            Paragraph("<b>In:</b> IRRequest<br/><b>Out:</b> IRResponse (FoodItem list)", body_style)
        ],
        [
            Paragraph("<b>4. Reasoning</b>", body_style),
            Paragraph("<b>Meal Planning Agent</b><br/>Port 8004", body_style),
            Paragraph("Explainable reasoning layer. Uses LLM (Claude/OpenAI) to reason over the retrieved food candidates and construct a transparent, explainable meal plan.", body_style),
            Paragraph("<b>In:</b> PlanningRequest<br/><b>Out:</b> MealPlan", body_style)
        ]
    ]

    t_flow = Table(flow_data, colWidths=[1.1 * inch, 1.4 * inch, 2.7 * inch, 1.8 * inch])
    t_flow.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_CARD),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t_flow)
    story.append(Spacer(1, 10))

    # Section 3: Shared Data Contract
    story.append(Paragraph("3. Shared JSON Contract (shared/schemas.py)", h1_style))
    story.append(Paragraph(
        "To guarantee zero schema drift between agents, all models are centralized in <code>shared/schemas.py</code>. No agent defines local duplicate schemas.",
        body_style
    ))

    schema_data = [
        [
            Paragraph("<b>Schema Model</b>", body_style),
            Paragraph("<b>Key Fields & Data Types</b>", body_style),
            Paragraph("<b>Usage Context</b>", body_style)
        ],
        [
            Paragraph("<b>UserProfile</b>", code_style),
            Paragraph("<code>user_id: str, goals: List[str], allergies: List[str], conditions: List[str], diet_type: Optional[str], calorie_target: Optional[int], preferences: List[str]</code>", code_style),
            Paragraph("Core user representation created by Intake Agent and consumed by IR & Planning Agents.", body_style)
        ],
        [
            Paragraph("<b>FoodItem</b>", code_style),
            Paragraph("<code>name: str, calories: float, protein_g: Optional[float], carbs_g: Optional[float], fat_g: Optional[float], source: str</code>", code_style),
            Paragraph("Individual factual food/nutrition record returned by the IR Agent.", body_style)
        ],
        [
            Paragraph("<b>IRRequest / IRResponse</b>", code_style),
            Paragraph("<code>IRRequest(profile: UserProfile, query: str)<br/>IRResponse(items: List[FoodItem])</code>", code_style),
            Paragraph("Data contract for semantic retrieval and constraint filtering.", body_style)
        ],
        [
            Paragraph("<b>MealPlan</b>", code_style),
            Paragraph("<code>user_id: str, meals: List[MealRecommendation(name, calories, reason, source)], disclaimer: str</code>", code_style),
            Paragraph("Final explainable response returned back up through the chain to the client.", body_style)
        ]
    ]

    t_schema = Table(schema_data, colWidths=[1.8 * inch, 3.2 * inch, 2.0 * inch])
    t_schema.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_CARD),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t_schema)
    story.append(Spacer(1, 10))

    # Section 4: Detailed Agent Specifications & Roadmap
    story.append(Paragraph("4. Individual Agent Specifications & Team Allocation", h1_style))

    # Member 1: Security Agent
    story.append(Paragraph("Member 1: Security & Validation Agent (Port 8001)", h2_style))
    story.append(Paragraph("<b>Primary Role:</b> API gateway, security perimeter, authentication, and sanitization.", body_style))
    story.append(Paragraph("• <b>Implemented / Current:</b> FastAPI service, <code>/health</code> check, regex-based prompt-injection blocking (e.g. 'ignore instructions', 'system prompt'), HTTP forwarding to Intake.", bullet_style))
    story.append(Paragraph("• <b>Deliverables & Next Steps:</b> Real JWT verification (<code>pyjwt</code>/<code>python-jose</code>), Fernet field-level encryption (<code>cryptography.fernet</code>) for health data, rate limiting with <code>slowapi</code>, structured trace-ID request logging.", bullet_style))
    story.append(Spacer(1, 4))

    # Member 2: Intake Agent
    story.append(Paragraph("Member 2: Intake & Profile Agent (Port 8002)", h2_style))
    story.append(Paragraph("<b>Primary Role:</b> Entity extraction and downstream pipeline coordination.", body_style))
    story.append(Paragraph("• <b>Implemented / Current:</b> FastAPI service, <code>/health</code> endpoint, sequential forwarding to IR Agent and Planning Agent.", bullet_style))
    story.append(Paragraph("• <b>Deliverables & Next Steps:</b> Replace keyword stub with real Named Entity Recognition (spaCy custom NER or LLM JSON extractor), profile persistence (SQLite), intent classification (new profile vs update).", bullet_style))
    story.append(Spacer(1, 4))

    # Member 3: Nutrition IR Agent (Our Implemented Agent)
    story.append(Paragraph("Member 3: Nutrition Information Retrieval (IR) Agent (Port 8003)", h2_style))
    story.append(Paragraph("<b>Primary Role:</b> Ground truth retrieval, vector indexing, and deterministic safety filtering.", body_style))
    story.append(Paragraph("• <b>Fully Implemented & Verified:</b><br/>"
                           "1. <b>Data Pipeline:</b> Cleaned USDA Foundation Foods (1,178 items) + curated balanced dishes with exact calories and macronutrients (protein, carbs, fat).<br/>"
                           "2. <b>Vector Engine:</b> Embedded ChromaDB vector database using <code>sentence-transformers</code> (<code>all-MiniLM-L6-v2</code>, 384 dimensions).<br/>"
                           "3. <b>Two-Stage Retrieval:</b> Contextual query enrichment -> Cosine similarity vector search -> Strict deterministic allergy/diet post-filtering (peanuts, gluten, dairy, vegan, keto).<br/>"
                           "4. <b>Verification:</b> Standalone test suite (<code>test_ir_agent.py</code>) and live FastAPI endpoints validated.", bullet_style))
    story.append(Spacer(1, 4))

    # Member 4: Meal Planning Agent
    story.append(Paragraph("Member 4: Meal Planning Agent (Port 8004)", h2_style))
    story.append(Paragraph("<b>Primary Role:</b> Explainable reasoning and meal recommendation synthesis.", body_style))
    story.append(Paragraph("• <b>Implemented / Current:</b> FastAPI service returning validated <code>MealPlan</code> structure.", body_style))
    story.append(Paragraph("• <b>Deliverables & Next Steps:</b> LLM integration (Anthropic Claude or OpenAI SDK), prompt grounding strictly constrained to <code>request.retrieved_items</code>, generating explicit explainable 'reason' strings tied back to user profile fields, safety guardrail against medical diagnosis.", bullet_style))
    story.append(Spacer(1, 8))

    # Section 5: Execution, Testing & Conventions
    story.append(Paragraph("5. Execution Guide & Best Practices", h1_style))
    story.append(Paragraph("<b>Running the Services:</b> Open 4 terminals and launch from repository root:", body_style))

    run_box_data = [[
        Paragraph(
            "<code># Terminal 1: uvicorn security_agent.main:app --reload --port 8001<br/>"
            "# Terminal 2: uvicorn intake_agent.main:app --reload --port 8002<br/>"
            "# Terminal 3: uvicorn ir_agent.main:app --reload --port 8003<br/>"
            "# Terminal 4: uvicorn planning_agent.main:app --reload --port 8004</code>",
            code_style
        )
    ]]
    t_run = Table(run_box_data, colWidths=[7.0 * inch])
    t_run.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_run)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>End-to-End Smoke Test Command:</b>", body_style))
    curl_box_data = [[
        Paragraph(
            "<code>curl -X POST http://localhost:8001/process \\<br/>"
            "&nbsp;&nbsp;-H \"Content-Type: application/json\" \\<br/>"
            "&nbsp;&nbsp;-d '{\"user_id\": \"u123\", \"raw_text\": \"I want to gain muscle, I am allergic to peanuts\"}'</code>",
            code_style
        )
    ]]
    t_curl = Table(curl_box_data, colWidths=[7.0 * inch])
    t_curl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_curl)
    story.append(Spacer(1, 10))

    # Section 6: Summary Checklist
    story.append(Paragraph("6. Project Evaluation Checklist", h1_style))
    story.append(Paragraph("• <b>Architectural Integrity:</b> Microservices maintain independence with zero circular dependencies and consistent schema adherence.", bullet_style))
    story.append(Paragraph("• <b>Ground Truth Information Retrieval:</b> IR Agent eliminates hallucinated nutrition by indexing real USDA FoodData Central records.", bullet_style))
    story.append(Paragraph("• <b>Responsible AI & Explainability:</b> Recommendations cite actual source datasets and provide clear user-centric justifications.", bullet_style))
    story.append(Paragraph("• <b>Course Deliverables:</b> Modular code repository, API documentation at <code>/docs</code> per agent, and full test suite.", bullet_style))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report successfully generated at: {output_path}")


if __name__ == "__main__":
    base_dir = pathlib.Path(__file__).resolve().parent
    out_file = str(base_dir / "NutriAgent_Project_Report.pdf")
    generate_pdf(out_file)
