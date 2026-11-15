# FinGuard AI

### Agentic AI-Powered Financial Document Verification and Exception Detection

FinGuard AI is an intelligent financial document verification system that combines OCR, machine learning, financial validation, duplicate detection, anomaly detection, and human-in-the-loop review.

## 1. Project Overview

The system aims to automate invoice analysis, identify financial inconsistencies, detect potential anomalies, and route exceptional cases for human review.

## 2. Key Features

- OCR-based invoice processing using PaddleOCR.
- Invoice field and line-item extraction.
- Financial and tax calculation verification.
- Purchase order matching.
- Duplicate invoice detection.
- Autoencoder and Isolation Forest anomaly detection.
- Multi-agent orchestration using LangGraph.
- Human-in-the-loop review dashboard.
- Reviewer authentication and role-based permissions.
- Audit history and API rate limiting.

## 3. Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Agent orchestration | LangGraph |
| OCR | PaddleOCR, PaddlePaddle, PaddleX |
| Machine learning | PyTorch, Transformers, Scikit-learn |
| Database | SQLite |
| Testing | Pytest |

## 4. System Architecture

```text
Financial Documents
        |
        v
Document Processing and OCR
        |
        v
Information Extraction
        |
        v
LangGraph Orchestrator
        |
        +--> Financial Verification Agent
        +--> Purchase Order Matching Agent
        +--> Duplicate Detection Agent
        +--> Anomaly Detection Agent
        |
        v
Supervisor Agent
        |
        +--> PASS
        |
        +--> Human Review
                   |
                   v
             Review Dashboard
                   |
                   v
               Audit History
```

## 5. Project Structure

```text
FinGuard_AI/
|-- config/
|-- frontend/
|-- models/
|-- src/
|   |-- agents/
|   |-- anomaly_detection/
|   |-- api/
|   |-- document_processing/
|   |-- duplicate_detection/
|   |-- extraction/
|   |-- human_review/
|   |-- orchestration/
|   |-- security/
|   |-- verification/
|-- tests/
|-- requirements-api.txt
|-- requirements-ml.txt
|-- requirements-ocr.txt
|-- .env.example
|-- .gitignore
|-- README.md
```

## 6. Installation

Clone the repository:

```bash
git clone https://github.com/edlasaiabhinay/FinGuard-AI.git
cd FinGuard-AI
```

Create a Python virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

Install API dependencies:

```bash
pip install -r requirements-api.txt
```

Install ML dependencies separately:

```bash
pip install -r requirements-ml.txt
```

OCR dependencies should be installed in a separate Python environment:

```bash
pip install -r requirements-ocr.txt
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

Note: Verify platform-specific PyTorch installation requirements before installing the ML dependencies.

## 7. Running the Application

Start the backend from the project root:

```bash
uvicorn src.api.main:app --reload
```

Backend API: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

## 8. Human Review API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/reviews/` | Review queue |
| GET | `/api/reviews/{case_id}` | Review case details |
| POST | `/api/reviews/{case_id}/decision` | Submit reviewer decision |
| GET | `/api/reviews/{case_id}/audit` | Audit history |

Review endpoints require appropriate authentication and permissions.

## 9. Testing

Run backend tests:

```bash
pytest -q
```

The recorded development regression run passed 92 tests. Re-run tests after making changes.

Build the frontend:

```bash
cd frontend
npm run build
```

## 10. Important Limitations

- Anomaly detection models require validation on larger representative real-world financial datasets.
- GSTIN format validation does not confirm registration against government records.
- The SROIE dataset used for LayoutLMv3 experimentation is not a dedicated GST invoice dataset.
- An anomaly flag indicates a need for investigation; it is not proof of fraud.
- SQLite audit triggers protect against ordinary SQL updates and deletes, not privileged database-file tampering.
- Production deployment requires secure secret management and appropriate infrastructure configuration.

## 11. Future Improvements

- Evaluation using larger real-world invoice datasets.
- Improved GST-specific document understanding.
- Enhanced financial anomaly detection.
- Explainable verification results.
- Advanced reviewer analytics.
- Production deployment and monitoring.

## 12. Repository

[FinGuard AI on GitHub](https://github.com/edlasaiabhinay/FinGuard-AI)

---

**FinGuard AI** — Agentic AI for intelligent financial document verification and exception detection.
