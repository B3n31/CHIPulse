# HCI Trend Analysis Project

This project collects structured data on Human–Computer Interaction (HCI) research papers from the OpenAlex API. It enables future analysis of trends, topics, citations, and more in the HCI community.

---

## 🔧 Setup Instructions

### 1. Navigate to the project root
```bash
cd path/to/hci_trend_analysis_project
```

### 2. Create and activate a virtual environment
```bash
# macOS / Linux
python3 -m venv hcitool-env
source hcitool-env/bin/activate

# Windows (PowerShell)
python -m venv hcitool-env
.\hcitool-env\Scripts\Activate.ps1
```

### 3. Install required packages
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📦 Requirements

File: `requirements.txt`
```
requests
pandas
tqdm
```

---

## 🚀 Run the Crawler

```bash
python scripts/hci_crawler.py \
  --start-year 2020 \
  --end-year 2024 \
  --output data/raw/hci_works.csv \
  --per-page 200 \
  --mailto your-email@example.com
```

---

## 📁 Output CSV Columns

- `title`
- `authors`
- `institutions`
- `year`
- `venue`
- `doi`
- `citation_count`
- `abstract`
- `concepts`
- `url`

---

## ✅ Future Plans

- Support automatic updates
- Add notebook-based and dashboard-style analysis
- Expand to other HCI-related venues
