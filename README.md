# Epi Evidence Extractor — How-To Guide

Extract structured epidemiological parameters from clinical PDFs in under
30 seconds per paper. Output is a table you can drop straight into a market model.

---

## Prerequisites

- Python 3.11+
- An Anthropic API key

---

## Setup (one time)

```bash
# 1. Navigate to the tool folder

# 2. Install dependencies
pip install -r requirements.txt

# 3. Confirm your API key is present (should already be set)
cat ../env          # look for ANTHROPIC_API_KEY=sk-ant-...
```

If you need to set the key manually, copy `.env.example` to `.env` in this
folder and paste your key:

```bash
cp .env.example .env
# then edit .env and add your key
```

---

## Running the App

```bash
python app.py
```

Gradio will print a local URL — open it in your browser:

```
Running on local URL:  http://127.0.0.1:7860
```

---

## Extracting Parameters from a PDF

### Step 1 — Upload

Click **"Upload PDF(s)"** and select one or more clinical PDFs from your
machine. You can upload multiple files at once or add files across multiple
uploads — each run appends new rows to the table.

### Step 2 — Extract

Click **"Extract Parameters"**. The status box will show progress:

```
Processing mack_partner3_2019.pdf...
✓ mack_partner3_2019.pdf done.
```

Each file takes 5–20 seconds depending on PDF length and API latency.

### Step 3 — Review the Table

Results appear as a dataframe. One row per paper, one column per field:

| Field | What it captures |
|-------|-----------------|
| `study_population_n` | Total enrolled N |
| `mean_age_or_range` | e.g. `"74.3 ± 8.1"` |
| `sex_distribution` | e.g. `"68.9% male"` |
| `disease_condition` | Primary condition studied |
| `disease_definition` | Echo criteria, ICD code, clinical definition |
| `prevalence_estimate` | With units and 95% CI if reported |
| `incidence_estimate` | With units and 95% CI if reported |
| `primary_outcome` | Primary endpoint |
| `follow_up_duration` | e.g. `"2 years"`, `"median 18.9 months"` |
| `country_geography` | Country or region |
| `data_source_type` | registry / claims / survey / trial / cohort |
| `publication_year` | 4-digit year |
| `journal_source` | Journal name |

Fields not reported in the paper show **`NR`**.

### Step 4 — Export

Click **"Export to CSV"**, then download the file from the **"Download CSV"**
link that appears. The CSV contains all rows accumulated in the current session.

---

## Building a Multi-Paper Evidence Table

Upload papers one batch at a time — rows accumulate without clearing:

1. Upload 5 papers → Extract → review
2. Upload 5 more → Extract → all 10 rows now in the table
3. Export to CSV when done

Click **"Clear Table"** to reset and start a new session.

---

## Recommended Test Papers

All are free to download:

| Paper | Why it's a good test |
|-------|---------------------|
| Mack et al., NEJM 2019 (PARTNER 3) | Dense trial stats, clear N and follow-up |
| Popma et al., NEJM 2019 (EVOLUT Low Risk) | Good age/sex distribution data |
| EARLY TAVR, NEJM 2024 | Recent; tests publication year extraction |
| ACC/AHA 2021 Valvular Guidelines | Long document; tests truncation handling |
| Any echo prevalence study for aortic stenosis | Tests prevalence + CI extraction |

---

## Troubleshooting

**"ANTHROPIC_API_KEY not found"**
The app looks for the key in `.env` first, then
`.env`. Make sure at least one exists with a valid key.

**Status shows ✗ filename failed**
- Confirm the file is a text-based PDF (not a scanned image — scanned PDFs
  have no extractable text layer).
- Very short or abstract-only PDFs may return mostly `NR` — that's expected.

**Table is empty after extraction**
Click Extract again after uploading — the upload and extract steps are
separate button clicks.

**Gradio port already in use**
```bash
python app.py --server-port 7861
```
Or kill the existing process and rerun.

---

## Cost Estimate

Each PDF extraction makes one API call to `claude-sonnet-4-6`.
A typical 10-page paper (~8k tokens input) costs roughly **$0.02–0.05**.
A 20-paper evidence table costs roughly **$0.40–$1.00** total.
