## Coverage feedback

Users can report unanswered, out-of-coverage, incorrectly supported, or
otherwise problematic responses via `POST /feedback`. Feedback is stored in
its own `feedback` table, separate from the retrieval corpus, together with a
snapshot of the answer's evidence status and cited section codes at the time
the report was made. It is intended for later review and aggregation to help
decide which areas of the corpus should be expanded.

User feedback never automatically modifies corpus documents, embeddings,
retrieval data, or prompts — it is review data only, always created with
`status = "new"`.

Feedback is anonymous: no IP address, browser fingerprint, or other tracking
data is stored, and no cookies or analytics are added. Users are asked in the
UI not to submit passport numbers, application numbers, or other sensitive
personal identifiers in their comment.
