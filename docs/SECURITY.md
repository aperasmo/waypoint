# Security

Waypoint uses practical security controls appropriate for a public web application and portfolio project.

The goal is to protect secrets, reduce unnecessary exposure and keep user input separated from trusted policy data.

## Secrets

Production secrets are supplied through environment variables.

Examples include:

- database credentials;
- OpenAI API credentials; and
- production origin settings.

Local secret files such as `.env.production.local` are ignored by Git and should never be committed.

The frontend must never contain server-side API keys or database credentials.

## CORS

The backend allows requests only from the configured frontend origin.

It does not use a wildcard production CORS policy.

Only the HTTP methods and headers required by the application are enabled.

## Database Exposure

In production, the database is placed on a private Docker network.

The frontend cannot connect directly to the database.

Requests flow through the backend API.

## Container Security

The production backend container runs as a non-root user.

The frontend is served from a non-root NGINX image.

Build tools are kept out of the final runtime images where practical.

## Input Validation

FastAPI and Pydantic validate incoming API payloads.

User-controlled fields have limits where appropriate.

For example, feedback comments, answers and cited-section lists are bounded rather than accepting unlimited input.

## Feedback Privacy

The feedback feature is designed to be anonymous.

Waypoint does not intentionally store:

- IP addresses;
- browser fingerprints; or
- analytics identifiers

through the feedback endpoint.

Users should still avoid submitting passport numbers, application numbers or other sensitive personal identifiers in feedback comments.

## Corpus Safety

Feedback never writes into the policy corpus.

It is stored separately for human review.

The application does not allow anonymous feedback to:

- change source documents;
- update embeddings;
- alter prompts; or
- modify retrieval rules.

## Source Updates

Waypoint does not automatically fetch or execute content from the INZ website.

Source pages are manually saved as MHTML and validated locally before they are converted into the corpus.

This creates a review point before external source material reaches the active database.

## Evaluation Safety

The project includes a leakage guard that checks production ranking code for direct references to evaluation data or hard-coded benchmark answers.

Run:

```bash
cd backend
uv run python -m scripts.check_eval_leakage
```

## Dependency and Deployment Practices

The project uses lock files for backend and frontend dependencies.

Production images are built from declared dependencies rather than from a developer's local environment.

Secrets should be injected at deployment time rather than stored in source control.

## Scope

Waypoint is not presented as a high-security or regulated enterprise platform.

Security work focuses on practical controls for the risks the application actually has:

- secret leakage;
- unsafe public input;
- unnecessary network exposure;
- accidental corpus modification;
- overly broad browser access; and
- deployment misconfiguration.

Additional controls such as platform rate limiting, monitoring or a web application firewall can be added at the hosting layer if the deployment requires them.
