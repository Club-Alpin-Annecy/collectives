---
name: collectives-review
description: Review the current branch of Collectives before opening a pull request, by running the "Code review" procedure of CODING.md and writing the result in the format the maintainers expect. Use before asking for a review.
---

# Review this branch like the maintainers do

Run the "Code review" procedure of `CODING.md` on the current branch, as a person or an agent would, and paste the result in the pull request description. The maintainer starts from it.

## Steps

1. Read `CODING.md` (the rules, the sensitive areas, the Code review procedure) and `AGENTS.md`.
2. Get the diff of the branch against `master`: `git diff master...HEAD`.
3. Run `uvx ruff format --check`, `uvx ruff check` and the test files related to the change.
4. Apply the rules to the lines the diff adds or changes, and nothing else. Every finding cites a rule ID of `CODING.md`, or `NEW` when no rule covers it.
5. Write the review in the format below. Write findings and questions in the language of the pull request (French for most pull requests).

## Output format

```
## Review — <PR title>
Verdict: APPROVE | APPROVE WITH COMMENTS | CHANGES REQUESTED
Checks run: ruff format ✓/✗ | ruff check ✓/✗ | tests: <files> ✓/✗
Merge readiness: ready | <what stands in the way: CI, conflicts, migration fork>
Sensitive areas touched: <list, or none>
Findings:
- [BLOCKING] path/to/file.py:42 — DB1 — <problem> — <proposed fix>
Questions for maintainers:
- <a product question the maintainers decide, never the reviewer>
Reading order: <files in the order to read them, for PRs over 400 changed lines>
```

The verdict is `CHANGES REQUESTED` as soon as there is one `BLOCKING` finding. The last two blocks appear only when they have content.

## Same check, run by the project's bot

To see what the automated review would say about a pull request without posting anything, from the repository root. Read the key into the environment without echo, so it is never typed in the command or kept in the shell history:

```
read -rs REVIEW_API_KEY; export REVIEW_API_KEY
REVIEW_API_BASE=<url> REVIEW_MODEL=<model> python3 .github/review/review_bot.py --repo Club-Alpin-Annecy/collectives --pr <number> --dry-run
```
