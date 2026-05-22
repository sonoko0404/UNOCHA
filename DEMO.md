# Demo

## 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 2. Run Dashboard

```bash
streamlit run app.py
```

Open the local Streamlit URL in the terminal output, usually `http://localhost:8501`.

## 3. Example Queries To Show

- Which crises in East Africa have less than 40% funding coverage?
- active HRPs with less than 40% funding coverage
- Show acute food insecurity hotspots with less than 10% requested funding.
- Countries with no HRP
- Which regions are consistently underfunded across multiple years?

## 4. What To Point Out In The Demo

- Ranked table
- Top result explanation
- Map-ready country output
- HRP status and HRP match confidence
- Funding coverage and funding gap
- CBPF allocation per person in need
- Chronic underfunding signal
- Data quality flags
- Severity context and its limitation
- Method and data audit panel

## 5. Important Framing

This is a decision-support tool for humanitarian analysts and donor advisors. It should help users ask better questions and prioritize review. It should not be used as an automated funding-allocation system.
