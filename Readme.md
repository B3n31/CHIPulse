# CHIPulse: A Human-Centered AI Interface for Scientometric Exploration

**(Lightweight README for Running the System)**

## Overview

CHIPulse is an interactive, data-centric system designed to explore 20 years of CHI Associate Chair (AC) data (2005–2025).
The system combines:

* A **structured SQLite database** containing AC identities, affiliations, committees, and publication histories
* An **LLM router** that plans and issues controlled SQL tool calls
* A **data-grounded generation module** that produces hallucination-free scientometric narratives

This repository includes all necessary data and the finalized database, so the system can be run immediately without re-scraping or rebuilding.

---

## Features

* **Structured SQL database** built from CHI AC lists and DBLP publications
* **Deterministic LLM routing** (planning → SQL → JSON)
* **Front-end interface** for interactive exploration
* **Traceable generation pipeline** ensuring factual correctness
* **No external knowledge** used during content generation

---

## Requirements

* Python 3.9+
* `pip`
* OpenAI API key (for GPT-5 Mini or equivalent)

All Python dependencies are listed in `requirements.txt`.

---

## Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv hcitool-env
source hcitool-env/bin/activate       # macOS / Linux

# Windows:
# .\hcitool-env\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file in the project root

```
OPENAI_API_KEY=your_key_here
```

The backend automatically loads this file.

---

## Running CHIPulse

### 1. Start the backend server

```bash
python scripts/api_server.py
```

If successful, Flask will display something like:

```
* Running on http://127.0.0.1:5000
```

### 2. Open the front-end UI

Simply open the Flask in your browser:


You can now submit questions such as:

* “Show me trends in CHI over the past decade”
* “Tell me something about SomeOne and his research trajectory”
* “Which institutions appear most frequently among CHI ACs?”

The system will:

1. Interpret your query
2. Plan SQL tool calls
3. Retrieve data from `database/chi_ac.db`
4. Generate a structured narrative based solely on the database

---

## Project Structure

```
├── data/
│   └── raw/                      # Original scraped committee data
│
├── database/
│   └── chi_ac.db                 # Final structured SQLite database (ACs, roles, pubs)
│
├── front-end/
│   ├── index.html                # UI
│   ├── script.js                 # Handles API calls and rendering
│   └── style.css
│
├── scripts/
│   ├── api_server.py             # Backend server (LLM router + SQL tools)
│   ├── llm_router.py             # Planning → SQL → JSON orchestration
│   ├── db_queries.py             # SQL tool functions
│   ├── build_db_from_csv.py      # (Not needed now; db already provided)
│   ├── dblp_fetch_publications.py
│   ├── scrape_committees.py
│   └── ...
│
├── sources/                      # PDF archives (optional)
├── requirements.txt
└── Readme.md
```

