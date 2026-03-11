"""
Epi Evidence Extractor
Upload a clinical PDF → extract structured epidemiological parameters → export CSV.
"""

import json
import os
import tempfile
from pathlib import Path

import anthropic
import gradio as gr
import pandas as pd
from dotenv import load_dotenv
from pypdf import PdfReader

# Load .env from this file's directory, then parent (edwards root)
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

EXTRACTION_FIELDS = [
    "study_population_n",
    "mean_age_or_range",
    "sex_distribution",
    "disease_condition",
    "disease_definition",
    "prevalence_estimate",
    "incidence_estimate",
    "primary_outcome",
    "follow_up_duration",
    "country_geography",
    "data_source_type",
    "publication_year",
    "journal_source",
]

SYSTEM_PROMPT = """You are a clinical epidemiology data extraction specialist.
Your job is to read clinical publications and extract structured epidemiological
parameters for use in medical device market models (e.g., for structural heart
disease at a company like Edwards Lifesciences).

Be precise. If a field is not reported in the paper, return the string "NR".
Never guess or hallucinate values — only extract what is explicitly stated.
Return ONLY valid JSON with no markdown fencing, explanation, or extra text."""

EXTRACTION_PROMPT = """Extract the following epidemiological parameters from the
clinical paper text below. Return a single flat JSON object with exactly these keys:

- study_population_n: Total N of the study population (integer or string with units)
- mean_age_or_range: Mean age or age range reported (e.g., "74.3 ± 8.1" or "65–80")
- sex_distribution: Sex breakdown (e.g., "58% male" or "42% female / 58% male")
- disease_condition: Primary disease or condition studied
- disease_definition: How the disease was defined (echo criteria, ICD code, clinical, etc.)
- prevalence_estimate: Prevalence figure with units and 95% CI if reported
- incidence_estimate: Incidence figure with units and 95% CI if reported
- primary_outcome: Primary outcome or endpoint
- follow_up_duration: Follow-up period (e.g., "2 years", "median 18.9 months")
- country_geography: Country or geographic region of the study
- data_source_type: One of: registry, claims, survey, trial, cohort, other
- publication_year: Year the paper was published (4-digit integer)
- journal_source: Journal name or source publication

Paper text:
---
{text}
---

Return only the JSON object."""


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def truncate_text(text: str, max_chars: int = 80_000) -> str:
    """Claude's context is large but we cap to keep costs predictable."""
    if len(text) <= max_chars:
        return text
    # Keep first 60k and last 20k — abstract/methods at start, conclusions at end
    return text[:60_000] + "\n\n[...truncated...]\n\n" + text[-20_000:]


def extract_epi_parameters(pdf_path: str, filename: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment.")

    raw_text = extract_text_from_pdf(pdf_path)
    text = truncate_text(raw_text)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT.format(text=text),
            }
        ],
    )

    raw_json = message.content[0].text.strip()
    try:
        result = json.loads(raw_json)
    except json.JSONDecodeError:
        # Attempt to salvage by finding the first {...} block
        start = raw_json.find("{")
        end = raw_json.rfind("}") + 1
        result = json.loads(raw_json[start:end]) if start != -1 else {}

    # Ensure all expected fields are present
    for field in EXTRACTION_FIELDS:
        result.setdefault(field, "NR")

    result["filename"] = filename
    return result


# ── State ──────────────────────────────────────────────────────────────────────
_rows: list[dict] = []


def process_upload(files) -> tuple[pd.DataFrame, str]:
    global _rows

    if not files:
        df = pd.DataFrame(_rows) if _rows else pd.DataFrame(columns=["filename"] + EXTRACTION_FIELDS)
        return df, ""

    status_lines = []
    for file in files:
        filename = Path(file.name).name
        try:
            status_lines.append(f"Processing {filename}...")
            row = extract_epi_parameters(file.name, filename)
            _rows.append(row)
            status_lines.append(f"✓ {filename} done.")
        except Exception as exc:
            status_lines.append(f"✗ {filename} failed: {exc}")

    cols = ["filename"] + EXTRACTION_FIELDS
    df = pd.DataFrame(_rows, columns=cols)
    return df, "\n".join(status_lines)


def clear_table() -> tuple[pd.DataFrame, str]:
    global _rows
    _rows = []
    return pd.DataFrame(columns=["filename"] + EXTRACTION_FIELDS), "Table cleared."


def export_csv(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", prefix="epi_extract_")
    df.to_csv(tmp.name, index=False)
    return tmp.name


# ── UI ─────────────────────────────────────────────────────────────────────────
with gr.Blocks(title="Epi Evidence Extractor", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # Epi Evidence Extractor
        Upload one or more clinical PDFs. The tool extracts structured
        epidemiological parameters using Claude and displays them as a table
        you can export to CSV.
        """
    )

    with gr.Row():
        upload = gr.File(
            label="Upload PDF(s)",
            file_count="multiple",
            file_types=[".pdf"],
        )

    with gr.Row():
        extract_btn = gr.Button("Extract Parameters", variant="primary")
        clear_btn = gr.Button("Clear Table", variant="secondary")

    status_box = gr.Textbox(label="Status", lines=4, interactive=False)

    results_table = gr.Dataframe(
        label="Extracted Epi Parameters",
        wrap=True,
        interactive=False,
    )

    with gr.Row():
        export_btn = gr.Button("Export to CSV")
        csv_file = gr.File(label="Download CSV", interactive=False)

    # Wire up
    extract_btn.click(
        fn=process_upload,
        inputs=[upload],
        outputs=[results_table, status_box],
    )
    clear_btn.click(
        fn=clear_table,
        outputs=[results_table, status_box],
    )
    export_btn.click(
        fn=export_csv,
        inputs=[results_table],
        outputs=[csv_file],
    )

if __name__ == "__main__":
    demo.launch()
