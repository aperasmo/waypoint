# Source and Limitations

Waypoint is intentionally limited by its source material.

Understanding that boundary is essential to understanding the project.

## Primary Source

Waypoint uses the publicly available **Immigration New Zealand Operational Manual** as its policy corpus.

Each indexed section records source information so the application can show users where supporting material came from.

Waypoint is an independent project and is not affiliated with or endorsed by Immigration New Zealand.

## What Waypoint Tries to Answer

Waypoint is designed to explain published rules contained in the indexed Operational Manual.

Examples include questions about:

- visa conditions;
- published eligibility requirements;
- work rights described in the manual;
- evidence requirements; and
- rules and exceptions stated in indexed sections.

The answer should remain grounded in the retrieved policy text.

## What Waypoint Does Not Try to Decide

Waypoint does not decide:

- whether a specific person will receive a visa;
- whether an application should be approved;
- how an immigration officer will exercise discretion;
- whether personal evidence will be accepted; or
- whether a person's circumstances satisfy a judgement-based test.

When personal facts materially affect the result, Waypoint should explain the rule and identify the missing information rather than make the decision for the user.

## Corpus Gaps

The current corpus is not assumed to contain every Operational Manual section.

If the answer requires policy that belongs in the Operational Manual but is not present in the indexed corpus, Waypoint should identify a **corpus gap**.

It should not fill the missing rule using the language model's general knowledge.

## External Information

Some questions cannot be answered from the Operational Manual alone.

A question may depend on information maintained somewhere else, such as:

- another government or official authority;
- a live service;
- a current fee or operational value;
- an external register; or
- another source of authoritative guidance.

In these cases Waypoint should identify that an **external source is required**.

## Currency of the Corpus

Waypoint does not automatically monitor the INZ website for changes.

Operational Manual pages are manually captured as MHTML, validated, reviewed and then processed into the corpus.

Because of this, there can be a delay between a change on the official website and the corresponding update in Waypoint.

For authoritative and current immigration information, users should always refer directly to Immigration New Zealand.

## General Information Only

Waypoint provides general information from its indexed source material.

It does **not** provide immigration advice.

Users who need advice about their individual circumstances should contact Immigration New Zealand or a licensed immigration adviser.

## Source Ownership

The Operational Manual and associated source material remain the property of their respective owner.

Waypoint uses structured copies for retrieval, evaluation and source-linked explanation.

The project should preserve source attribution and avoid presenting the policy text as original Waypoint content.

## Feedback Is Not Policy

User feedback is review data only.

It is not treated as an authoritative immigration source and never automatically changes:

- the corpus;
- embeddings;
- retrieval logic; or
- answer prompts.

## Design Boundary

Waypoint deliberately prefers a limited, evidence-grounded response over an answer that sounds helpful but is not supported by the available source.

That boundary is a core part of the project rather than a failure mode.
