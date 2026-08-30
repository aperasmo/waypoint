# Waypoint Architecture

This document gives a simple overview of how Waypoint works.

## Main Parts

Waypoint has four main parts:

```text
Frontend
   ↓
FastAPI backend
   ↓
Search + evidence checks
   ↓
PostgreSQL / pgvector
```

### Frontend

The frontend is built with React and Vite.

It provides three main user experiences:

- **Ask** — ask a question and receive an evidence-grounded response.
- **Browse** — browse indexed Operational Manual sections directly.
- **Feedback** — report an answer or source that appears incorrect or incomplete.

The frontend does not contain immigration rules or secret API keys.

### Backend

The FastAPI backend handles requests from the frontend.

The main routes are:

- `/ask`
- `/browse/categories`
- `/browse/sections`
- `/browse/sections/{section_code}`
- `/feedback`
- `/health`

The backend is responsible for retrieval, answer generation, citations, data access and validation.

## Ask Flow

The main question flow is:

```text
Question
   ↓
Expand known acronyms
   ↓
Semantic search + keyword search
   ↓
Merge and rank results
   ↓
Send retrieved policy to answer model
   ↓
Check evidence boundary
   ↓
Return answer + citations
```

### Search

Waypoint uses two search approaches together.

**Semantic search** helps when the user and the Operational Manual use different wording.

**Keyword search** helps when exact terms, visa names, section codes or abbreviations matter.

The results are combined into one ranked list before the answer is generated.

### Evidence-Grounded Answering

The language model is not asked to answer from general immigration knowledge.

It receives the retrieved Operational Manual sections and is instructed to explain only what those sections support.

The response includes citations back to the retrieved policy.

## Evidence Status

Waypoint separates three situations.

### Sufficient

The retrieved Operational Manual sections contain the policy needed to explain the question.

### Corpus gap

The answer requires Operational Manual material that is not present in the current corpus.

Waypoint should identify the gap rather than fill it from memory.

### External source required

The question depends on authoritative information that belongs outside the Operational Manual.

Examples can include live service information, external agency information or other current data not maintained in the manual.

## Decision Boundary

Evidence can be sufficient while a user's personal result is still uncertain.

Waypoint therefore keeps policy evidence separate from personal decision-making.

It distinguishes between:

- **general information** — the published rule can be explained directly;
- **case-specific application** — additional personal facts materially affect the result; and
- **discretionary judgement** — the outcome depends on judgement by an authorised decision-maker.

Waypoint explains the published rule but does not make the final immigration decision for the user.

## Browse Flow

The browse feature does not use the language model.

It reads the indexed sections directly from the database and allows users to inspect the corpus by category or section.

This gives users a second way to explore the source material without asking a question.

## Feedback Flow

Feedback is stored separately from the retrieval corpus.

A feedback report can include:

- the question;
- feedback type;
- an optional comment;
- the evidence status shown to the user;
- a snapshot of the answer; and
- cited section codes.

Feedback never automatically changes the corpus, embeddings, retrieval logic or prompts.

## Data Layer

PostgreSQL stores:

- Operational Manual sections;
- chunks used for retrieval;
- embeddings; and
- feedback.

pgvector is used for semantic similarity search.

The production database is separate from the manually archived MHTML source files.

## Design Principle

Waypoint is designed around a simple rule:

> Retrieval should provide the evidence, and the answer should stay inside that evidence.

This is more important to the project than making the system answer every possible immigration question.
