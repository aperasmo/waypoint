# Waypoint

**Waypoint** is an evidence-grounded AI application for exploring the publicly available **Immigration New Zealand Operational Manual**.

It helps users find relevant immigration policy and understand what the published manual says, while showing the sections used to support each response.

**Live demo:** https://waypoint.aperasmo.com/

> Waypoint is an independent project. It is not affiliated with or endorsed by Immigration New Zealand and does not provide immigration advice.

## Why Waypoint?

Immigration policy can be difficult to navigate because relevant information may be spread across multiple sections of a large operational manual.

Waypoint was built to explore how AI and traditional software engineering can work together to make that information easier to search without allowing the AI to freely invent or rely on unsupported immigration knowledge.

The core principle is simple:

**If the available evidence does not support an answer, Waypoint should say so.**

## What It Does

Waypoint allows users to:

- ask questions about policies contained in the Operational Manual;
- see the policy sections used to support an answer;
- browse indexed Operational Manual sections directly;
- identify when required policy is missing from the current corpus;
- identify when a question depends on information outside the Operational Manual; and
- submit anonymous feedback when an answer or source appears incorrect.

Waypoint is designed to explain published rules rather than decide whether a person qualifies for a visa or whether an application will be approved.

## How It Works

```text
User question
     ↓
Semantic + keyword search
     ↓
Relevant Operational Manual sections
     ↓
Evidence check
     ↓
Grounded answer with citations
```

Waypoint combines semantic search with keyword search. This helps it find relevant policy even when a user's wording differs from the wording used in the Operational Manual.

The retrieved sections are then provided to the answer model. The model is instructed to use only that evidence when explaining the policy.

When the evidence is incomplete, Waypoint distinguishes between:

- **Sufficient** - the retrieved manual sections contain the policy needed to explain the question.
- **Corpus gap** - relevant Operational Manual material is missing from the current corpus.
- **External source required** - the answer depends on information maintained outside the Operational Manual.

## Technology

Waypoint uses:

- **React + Vite** for the frontend
- **FastAPI** for the backend
- **PostgreSQL + pgvector** for storage and retrieval
- **OpenAI embeddings and language models**
- **Docker** for consistent development and deployment

## Project Structure

```text
waypoint/
├── backend/
│   ├── app/          # API, retrieval and data models
│   ├── scripts/      # Corpus maintenance and evaluation tools
│   └── tests/        # Active tests and evaluation questions
├── frontend/         # React web application
├── data/             # Corpus, manifest and supporting data
├── docs/             # Project documentation
├── docker-compose.yml
└── README.md
```

## Updating the Corpus

Waypoint does not automatically collect pages from the Immigration New Zealand website.

Operational Manual pages are manually saved as **MHTML** files and processed locally.

```text
Manual MHTML capture
        ↓
Validate archive
        ↓
Extract policy content
        ↓
Build staging corpus
        ↓
Compare and audit
        ↓
Update active corpus
        ↓
Embed changed content
        ↓
Evaluate
```

See [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) for the workflow.

## Local Development

### 1. Start PostgreSQL

```bash
docker compose up -d
```

The local database is exposed on port `5434`.

### 2. Configure the backend

Create `backend/.env`:

```text
OPENAI_API_KEY=your_key
DATABASE_URL=postgresql+asyncpg://waypoint:waypoint123@localhost:5434/waypoint
CORS_ORIGIN=http://localhost:5174
ENVIRONMENT=development
```

Then:

```bash
cd backend
uv sync
uv run python -m scripts.init_db
uv run python -m scripts.ingest
uv run uvicorn app.main:app --reload --port 8100
```

### 3. Start the frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5174`.

## Tests and Evaluation

Run backend tests:

```bash
cd backend
uv run pytest
```

Run retrieval evaluation:

```bash
uv run python -m scripts.evaluate
```

Run answer evaluation while the backend is running:

```bash
uv run python -m scripts.evaluate_answers
```

See [`docs/EVALUATION.md`](docs/EVALUATION.md) for more information.

## Documentation

- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) - how the main parts work together
- [`DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) - how Operational Manual content is updated
- [`EVALUATION.md`](docs/EVALUATION.md) - how retrieval and answers are checked
- [`SECURITY.md`](docs/SECURITY.md) - practical security decisions
- [`SOURCE_AND_LIMITATIONS.md`](docs/SOURCE_AND_LIMITATIONS.md) - source boundaries, attribution and limitations

Deployment instructions remain in:

- `WAYPOINT_DEPLOYMENT.md`
- `WAYPOINT_DEPLOYMENT_RUNBOOK.md`

## Source and Disclaimer

Waypoint uses material from the publicly available **Immigration New Zealand Operational Manual**.

Source material remains the property of its respective owner. Waypoint stores structured copies for retrieval and links responses back to the relevant source where available.

The corpus may not always contain every Operational Manual section or the latest version of every policy.

Waypoint provides **general information only**. It does not provide immigration advice and should not be used as a substitute for Immigration New Zealand, a licensed immigration adviser, or another appropriate professional authority.

## Feedback

Users can report answers that appear unsupported, incomplete, outside the current coverage, or linked to irrelevant sources.

Feedback is stored separately from the retrieval corpus and does not automatically modify policy content, embeddings, prompts, or answers.
