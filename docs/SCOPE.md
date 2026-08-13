# INZ RAG Assistant — Project Scope Document

**Author:** Allan
**Status:** Draft v1
**Date:** August 2026

---

## 1. Project Overview

This project is a Retrieval-Augmented Generation (RAG) system built on top of the Immigration New Zealand (INZ) Operational Manual. The idea started from a personal need: Allan is going through his own PSWV and family SMC application, and wanted a hands-on RAG project that connects to something real, not just a generic demo dataset.

For me, this project works on two levels. First, it is a genuine technical portfolio piece that shows RAG applied to a real, regulated, and complex document set. Second, it doubles as a study companion for Allan's own visa journey, though not as a replacement for official advice.

---

## 2. Objectives

**Primary objective**
Build a working RAG system that retrieves and cites relevant sections of the INZ Operational Manual in response to user questions, without generating personalized advice.

**Secondary objective (portfolio)**
Demonstrate structure-aware chunking, citation-grounded generation, and update handling for a live, regularly-changing policy document. This is a strong differentiator for full-stack and AI/ML-adjacent roles in the NZ market.

---

## 3. Core Principle: No Advice, All Evidence-Based

This is the non-negotiable design constraint for the whole project.

Immigration advice in New Zealand is regulated under the Immigration Advisers Licensing Act 2007. Giving advice tailored to a person's individual situation, for a fee or regularly, requires a licence. Publishing or retrieving publicly available information does not.

To stay clearly on the information side of that line, the system follows these rules:

1. Every answer must be traceable to a specific clause or section of the Operational Manual.
2. The system never says "you should," "you qualify," or "I recommend." It only reports what the manual states.
3. No eligibility scoring, no personalized recommendation engine, no case-specific interpretation.
4. Every response includes a visible disclaimer (see Section 9).
5. If a question cannot be answered by quoting or paraphrasing the manual directly, the system says so instead of guessing.

This constraint should be enforced at the prompt level (system prompt for the LLM) and at the product level (UI copy, no "ask about my case" framing).

---

## 4. Handling Questions Outside Current Coverage

Real testing (the Vian scenario, see project chat history) surfaced something the design didn't originally account for: not every wall the app hits is the same kind of wall, and each kind needs a different response, not a generic "I don't know."

**Three distinct wall types, each needs its own fallback:**

**Type A — Corpus coverage gap.** The topic exists in the manual, but hasn't been scraped/indexed yet (e.g. a visa category outside current scope). Retrieval returns nothing relevant.

> *Example response:* "I don't have that section indexed yet. You can check it directly: go to immigration.govt.nz/opsmanual and use the table of contents to find [topic/section code if known]."

**Type B — Requires live/external data the manual itself doesn't contain.** The manual states a *rule* but points to a separate live system for the actual data, ANZSCO occupation codes, whether a specific employer is currently accredited, current wage rates. No amount of scraping the manual fixes this, the data structurally lives elsewhere. This is exactly what happened with Vian's case: the manual says "check ANZSCO" and "employer must be accredited," but doesn't contain the ANZSCO code lookup or the accreditation registry itself.

> *Example response:* "This needs a live check outside the manual. Here's exactly where: [named tool, e.g. INZ's 'Check if an employer is accredited' page]. Steps: 1) Go to immigration.govt.nz, 2) Search '[tool name]', 3) [specific action, e.g. enter the employer's NZBN or name]."

Phase 2 closes part of this gap directly (ANZSCO lookup + live accreditation check as built-in features, see Roadmap). Until then, Type B responses must name the *specific* official tool and give real steps, not a vague "check elsewhere."

**Type C — Requires case-specific judgment, not just more data.** Whether someone's actual job duties "substantially align" with their job title, whether a specific application will be approved, anything that requires an immigration officer's or adviser's discretion. This is never solved by scraping more, it's structurally outside what a published-rules RAG tool can or should answer, tied directly to the no-advice principle in Section 3.

> *Example response:* "This depends on a judgment call specific to your situation, the kind an immigration officer or licensed adviser makes case by case, not something published policy alone can answer. I can tell you what the criteria are, that's the evidence you'd need to show, but not whether your specific case meets it. To get that: find a licensed immigration adviser at iaa.govt.nz (the Immigration Advisers Authority register), or contact INZ directly."

**Implementation approach for Phase 1 (before any classifier exists):** this doesn't need new infrastructure yet, it needs the generation prompt itself to recognize these patterns. The system prompt for the Ask feature's LLM should explicitly instruct it to detect when retrieved manual content references something requiring external lookup (phrases like "see ANZSCO," "must be accredited," "an immigration officer may consider") and produce the appropriate structured fallback instead of vaguely paraphrasing a dead end. Getting this prompt behavior right matters as much as the retrieval quality itself, a technically correct citation that leaves someone stuck is still a bad answer.

---

## 5. Data Source

**Primary source:** INZ Operational Manual (publicly published, updated regularly by INZ under section 25 of the Immigration Act 2009)
Source: https://www.immigration.govt.nz/opsmanual/

**Initial scope (v1), to keep it manageable:**
- Residence — Skilled Migrant Category (SMC)
- Temporary Entry — Post Study Work Visa (PSWV)
- Generic sections that apply across residence and temporary entry

Later phases can expand to other visa categories once the core pipeline is proven.

**Update handling:** INZ publishes changes through Amendment Circulars, incorporated into the manual on the day they take effect. The system needs a scheduled re-check and re-index job, not a one-time scrape.

**Important distinction to carry into the actual app build (not just local dev):** the `collect_manual.py` / `check_for_updates.py` scripts used to build this dataset are a local, developer-run pipeline, good for standing up the corpus, not good enough for production. The real Waypoint app needs its own built-in fetch feature: a background job inside the FastAPI backend (not something Allan runs manually on his laptop) that periodically re-checks INZ for changed and new sections, re-embeds only what changed, and keeps the live app current without human intervention. This should productionize the same change-detection approach already proven locally (compare the "Effective DD/MM/YYYY" date per clause, not just file existence), running on a schedule via the backend's task scheduler (e.g. APScheduler, matching the pattern already used in Allan's other projects) rather than Windows Task Scheduler. Noted here for Phase 1/2 architecture so it doesn't get missed when the actual backend is built.

**Change-detection must not rely on the effective-date field alone.** Testing against the real manual surfaced pages (e.g. A4.20) that almost certainly do carry an "Effective" date on the live site, but where date extraction failed locally, most likely a page-structure quirk rather than the page genuinely lacking a date. A detector that only compares dates would silently stop catching updates to any page where extraction fails, exactly the kind of quiet failure an unattended background job must not have. The production fetch job should use the date as the primary signal, and fall back to comparing a hash of the extracted body text whenever no date is found, so content changes on those pages still get caught rather than skipped forever.

**Temporal handling for announced-but-not-yet-effective changes.** The corpus now includes a pending-changes file (`PENDING-SMC-2026.md`) describing SMC changes that take effect 24 August 2026, alongside the current SR3.x clauses that remain correct until then. This creates a real retrieval risk: if both are embedded with no temporal metadata, a query today ("how many points for a bachelor's degree") could surface either the current answer (3 points) or the future one (4 points) depending on chunk similarity, not on which is actually in force on the day the question is asked. The retrieval layer needs to either (a) filter out or down-rank not-yet-effective content based on the current date vs. each chunk's `takes_effect_date`, or (b) when a pending change exists for a topic, surface both explicitly labelled as "currently" vs "from 24 August 2026" rather than picking one silently. Option (b) is probably better for a tool whose whole value proposition is not misleading people. Needs deciding before chunking starts, since it affects what metadata each chunk needs to carry.

---

## 6. System Design

**High-level flow:**
1. Ingestion: pull manual sections for the scoped categories, preserve section/clause structure.
2. Chunking: chunk by clause/sub-clause boundaries, not fixed character count, so citations stay accurate.
3. Embedding: generate vector embeddings per chunk, store with metadata (section number, title, last-updated date).
4. Retrieval: on a user query, retrieve top-matching chunks.
5. Generation: LLM paraphrases retrieved chunks into a plain-language answer, with inline citation to section/clause.
6. Citation check: response is rejected or flagged if it cannot be tied back to a retrieved chunk.

**Prompt-level constraint example (for the system prompt):**
"Answer only using the provided context. Do not give personal recommendations or eligibility opinions. Cite the section number for every claim. If the context does not contain the answer, say so."

---

## 7. Tech Stack

Reusing what you already know from the glaucoma capstone, so the learning curve stays on the RAG part, not the plumbing:

- **Backend:** FastAPI
- **Database:** PostgreSQL with pgvector extension (vector storage without adding a separate vector DB)
- **Embeddings:** open-source embedding model (e.g. sentence-transformers) to start, cloud fallback later if needed
- **LLM layer:** local model via Ollama for development, cloud fallback (same pattern as your AI Git Assistant) for production quality
- **Scheduler:** APScheduler for periodic re-index jobs, same as your glaucoma backend
- **Frontend:** React, simple chat interface with citation links
- **Deployment:** Render or similar, matching your existing deployment pattern

---

## 8. MVP Feature List

- Chat-style query interface
- Answers grounded in retrieved manual sections, with visible citation (section number + link)
- "Not covered" response when the manual doesn't answer the question
- Basic section browser (view the manual by category, outside of chat)
- Scheduled re-index job for manual updates

---

## 9. Out of Scope (v1)

Explicitly excluded to protect the no-advice boundary and keep the MVP achievable:

- Personalized eligibility calculators or scoring
- Application form filling or submission
- Case-specific recommendations ("what should I apply for")
- Payment processing or paid advice features
- Multi-language support (can be a later phase)

---

## 10. Disclaimer (for the app UI)

Draft text to display prominently in the app, not buried in fine print:

> This tool provides general information sourced directly from the publicly available INZ Operational Manual. It does not provide immigration advice and is not a substitute for advice from a licensed immigration adviser or INZ. For advice on your specific situation, consult a licensed immigration adviser or contact Immigration New Zealand directly.

---

## 11. Monetization Path (if pursued later)

Given the legal boundary discussed, the safer paths are:

1. **B2B tool for licensed advisers** — sell as a research/productivity tool to advisers who remain the ones giving advice. Lowest legal risk.
2. **Free portfolio tool** — no monetization in v1, used purely as a demonstrated skill for job applications.
3. **Referral model** — free info tool, refers users needing personalized help to licensed advisers, adviser pays referral fee.

Direct monetization to end-users asking personalized questions is not recommended without legal review first.

---

## 12. Roadmap

**Phase 1 — Proof of Concept**
Ingest SMC and PSWV sections only. Basic retrieval + citation. No frontend yet, test via API. Includes the Type A/B/C fallback prompt behavior from Section 4, since Phase 1 has to handle hitting walls gracefully even before Phase 2's lookups exist.

**Phase 2 — External Data Lookups (ANZSCO + Employer Accreditation)**
Closes the Type B gap from Section 4 directly, instead of just pointing people to INZ's own tools. Two integrations:
- **ANZSCO occupation lookup**: given a job title, return the correct ANZSCO code and skill level (this is what resolved the wage-threshold question in Vian's case, University Lecturer vs Polytechnic Teacher isn't a minor distinction, it changes which wage threshold applies).
- **Employer accreditation check**: query INZ's accreditation status directly (by NZBN or name) instead of telling the user to go check it themselves.

Both are separate data sources from the Operational Manual corpus, and need their own update/freshness handling, accreditation status in particular can change.

**Phase 3 — Evaluation**
Test retrieval accuracy and citation correctness against known manual clauses. Refine chunking strategy.

**Phase 4 — Frontend**
Build the chat UI, section browser, citation display.

**Phase 5 — Deployment**
Deploy, add scheduled re-index job, write up as portfolio case study.

**Phase 6 (optional) — Monetization test**
Explore adviser B2B angle if there's interest, after legal boundary is confirmed comfortable.

---

## 13. Notes for Portfolio / Interview Narrative

This project pairs well with your own PSWV and SMC journey as a story. For interviews, the value is not just "I built a RAG app." It's "I built a RAG app for a regulated, real-world document set, where I had to design around a legal constraint, not just a technical one." That is a stronger signal than a generic RAG demo.
