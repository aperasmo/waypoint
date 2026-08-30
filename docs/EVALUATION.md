# Evaluation

Waypoint is evaluated at more than one level.

A search system can retrieve the wrong evidence even if the language model is capable of writing a good answer. Likewise, correct evidence can still be used badly.

Waypoint therefore checks retrieval and answer behaviour separately.

## 1. Unit Tests

Run:

```bash
cd backend
uv run pytest
```

The active tests cover important backend behaviour, including feedback validation and the current source-boundary classifier contract.

The exact number of tests may change as the project develops, so the repository should rely on the current test run rather than a fixed number written in documentation.

## 2. Retrieval Evaluation

Run:

```bash
uv run python -m scripts.evaluate
```

This uses the questions in:

```text
backend/tests/eval_questions.json
```

The main retrieval measures are:

### Recall@1

Was an expected policy section the first result?

### Recall@5

Was an expected policy section present somewhere in the first five results?

Recall@5 is especially important because the answer stage can only use evidence that retrieval actually provides.

A high retrieval score does not automatically mean the final answer is correct. It only shows whether the required evidence reached the answer stage.

## 3. Ranking Diagnostics

Run:

```bash
uv run python -m scripts.diagnose_ranking
```

This helps inspect questions where the correct section was not ranked first.

It shows how the semantic and keyword search components behaved and helps identify whether a miss came from retrieval rather than answer generation.

## 4. Answer Evaluation

With the backend running:

```bash
uv run python -m scripts.evaluate_answers
```

This evaluates the `/ask` endpoint against the expected answer contract.

It checks:

- evidence-status accuracy;
- decision-boundary accuracy;
- expected citation coverage;
- classification stability across repeated runs; and
- the overall outcome derived from those classifications.

The script also writes:

```text
backend/tests/answer_review.md
```

This report supports manual review of answers.

## 5. Manual Review

Some important qualities should not be reduced to one automatic score.

The answer review is used to check whether:

- the answer stays inside the cited evidence;
- unsupported policy is introduced;
- the system makes a personal immigration decision;
- missing-information requests are actually necessary; and
- important figures, dates or thresholds are supported by the cited section.

## 6. Evaluation Leakage Guard

Run:

```bash
uv run python -m scripts.check_eval_leakage
```

This checks the production ranking path for direct benchmark leakage, including:

- imports from test data;
- exact benchmark questions embedded in runtime code; and
- hard-coded section codes in ranking logic.

Passing this check does not prove that a system will generalise perfectly, but it helps prevent obvious forms of benchmark overfitting.

## What Evaluation Does Not Prove

Evaluation results should be read carefully.

They do not prove that:

- every Operational Manual section is present;
- every possible immigration question can be answered;
- the source material is currently complete;
- a generated answer is immigration advice; or
- the system can decide an individual's eligibility.

The purpose of evaluation is narrower:

**to measure whether Waypoint retrieves and uses its available evidence in a controlled and repeatable way.**
