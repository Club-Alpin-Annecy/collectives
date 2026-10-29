
# Coding rules

These rules apply to every contribution, whether written by a human or by an
AI agent, and they are the reference for every code review. Each rule has an
ID (e.g. `DB2`) so that review findings can cite it.

If a review finds a recurring problem that no rule covers, propose a new rule
here in the same PR.

## General
 * **GEN1** Keep it simple (KISS): prefer the simplest solution that meets
   the need. No speculative abstraction, configuration or generalisation
   for cases that do not exist yet; reuse existing helpers before adding
   new ones.
 * **GEN2** One concern per PR. No IDE, personal or debug files
   (`launch.json`, `.vscode/`, `console.log`, `breakpoint()`).

## Product
 * **PROD1** A need specific to one activity is met by configuration (an
   activity type option or a configuration item), not by code written for
   that activity.
 * **PROD2** Collectives is shared by several clubs, and a feature should
   serve all of them. When only some clubs need it, it is off by default,
   leaves no trace when off (no menu, route, log or scheduled task), and is
   tested both off and on.
 * **PROD3** A new module, data domain or outside integration should name
   who will maintain it in the PR description.
 * **PROD4** Prefer an extension point (a setting, a switch, the API, an
   outside integration) to changing core behaviour. A PR that changes
   existing behaviour for every user says so in its description and needs a
   maintainer decision.
 * **PROD5** Prefer hot configuration to cold. Anything a club may want to
   change (texts, thresholds, switches, the club's identifiers on other
   services) is an item in `collectives/configuration.yaml`, editable from
   the site without a restart. `config.py` and `instance/config.py`, read
   once at start-up, keep only what the server needs to start (secret key,
   database, paths) or what must never be editable from the site.

## Python style
 * **PY1** Always format Python code using [ruff](https://astral.sh/ruff) (`uvx ruff format`).
 * **PY2** Follow the guidelines from https://google.github.io/styleguide/pyguide.html, except:
   * for Section 3, "Python Style rules" -- there `ruff` should prevail
   * import (see 2.2), where import of functions and classes are authorized.
 * **PY3** Code should be validated with `ruff check` as configured in `pyproject.toml`.
 * **PY4** Documentation shall be updated for every commit which modify a class or method parameters.
   Docstrings follow the Google convention.
 * **PY5** No magic strings or values repeated across the code: use an `Enum`
   or a named constant.
 * **PY6** Importing a module must not have side effects (no registration,
   I/O or configuration reads at import time); do it explicitly at app init.
 * **PY7** No dead code: remove unused functions, parameters, templates and
   commented-out code.
 * **PY8** Prefer guard clauses (early `return`, `continue`, `raise`) to
   nested `if`/`else` blocks: handle invalid or special cases first and
   exit, so that the main path stays at the lowest indentation level.
   ```python
   # Avoid
   def can_register(user, event):
       if user.is_active:
           if not event.is_full():
               return True
           else:
               return False
       else:
           return False

   # Prefer
   def can_register(user, event):
       if not user.is_active:
           return False
       if event.is_full():
           return False
       return True
   ```

## HTML and user interface
 * **HTML1** Indent with spaces.
 * **UI1** Text shown to users follows French spelling conventions
   (`événement`, not `évènement`).
 * **UI2** Every page works on a phone: no horizontal scrolling, nothing cut
   off, buttons and fields usable by touch. Check a new or changed page at
   phone width before asking for a review.

## All language types
 * **ALL1** Do not add blank spaces at end of line.
 * **ALL2** Never align with tabs, always using spaces.
 * **ALL3** Code, identifiers, comments and docstrings are in English; text
   shown to users (templates, `flash()` messages, emails) is in French.

## Database and migrations
 * **DB1** Code and migrations must work on both SQLite (development, tests)
   and MariaDB (production). For instance, MariaDB cannot index a `Text`
   column without a prefix length: use a bounded `String(n)` for indexed
   columns.
 * **DB2** Every model change comes with an Alembic migration in
   `migrations/versions/`.
 * **DB3** Data migrations must not silently broaden access. For instance,
   removing the last condition of a `UserGroup` makes it match every active
   user.

## Security and configuration
 * **SEC1** New routes are protected with the decorators of
   `collectives/utils/access.py` (`valid_user`, `confidentiality_agreement`,
   `user_is`...) or by the blueprint `before_request`; API endpoints check
   access as well.
 * **SEC2** New secret configuration items in
   `collectives/configuration.yaml` (passwords, keys, tokens) are marked
   `hidden: true`. Non-hidden identifiers of the club on third-party
   services are added to `SECRET_CONFIGURATION_ITEMS` in
   `collectives/utils/anonymize.py`.
 * **SEC3** Never log or display secrets or personal data that is not needed.
 * **SEC4** Uploaded documents other than images are served as attachments
   (`Content-Disposition: attachment`), never rendered by the browser.
 * **SEC5** A route acting on one event, user or role checks the rights on
   that object (for instance `event.has_edit_rights`), not only the user's
   general role.

## Performance
 * **PERF1** No database query per item inside a loop: load what the loop
   needs once.

## External services
 * **EXT1** Every call to an external server (HTTP, SOAP, SMTP...) has a
   timeout taken from the configuration, e.g. `Configuration.EXTRANET_TIMEOUT`
   in `collectives/utils/extranet.py` or `Configuration.SMTP_TIMEOUT` in
   `collectives/utils/mail.py`.

## Tests
 * **TEST1** A `[FIX]` comes with a regression test; a `[FEATURE]` comes with
   tests of its main paths. CI requires at least 60% coverage.
 * **TEST2** Reuse the fixtures from `tests/fixtures/`. Never combine two
   `*_client` fixtures in one test: use `client` and
   `fixtures.client.login()` to switch users.
 * **TEST3** Locally, run the test files related to the change
   (`uv run pytest tests/<file>`) rather than the whole suite.

## Commit
 * **COM1** Message in English.

## Github merge
(for project maintainers)
 * **COM2** Add a tag in merge commit message (eg. [FEATURE] xxxxxxx )
   * `[FEATURE]` : contains a new feature.
   * `[FIX]` : fix a bug
   * `[INTERNAL]` : no functional changes (refactoring, documentation, test, performance, etc...)
   * `[OTHER]`
   * Don't include if it should not be in release note.
 * **COM3** If the PR is linked to an issue, use [github link in commit](https://help.github.com/en/github/managing-your-work-on-github/linking-a-pull-request-to-an-issue#linking-a-pull-request-to-an-issue-using-a-keyword) just after the tag. in merge commit, eg:
   * `[FIX] Fixes #123 : event list title fixed`
   * `[FEATURE] Closes #124 : add info on event`

Note: to generate release note:
``` for tag in FEATURE FIX INTERNAL OTHER ; do echo $tag:;  git log --pretty="%s" --grep="\[$tag\]" v0.5..v0.6  ; echo; done ```

# Sensitive areas

Changes touching these areas always need the approval of a human maintainer,
whatever the review verdict:
 * payment: `collectives/models/payment.py`, `collectives/utils/payment.py`,
   `collectives/utils/payment_provider/`, `collectives/routes/payment.py`,
   `collectives/api/payment.py`
 * authentication, roles and permissions: `collectives/routes/auth/`,
   `collectives/models/auth.py`, `collectives/models/role.py`,
   `collectives/models/user_group.py`, `collectives/utils/access.py`
 * database migrations: `migrations/`
 * configuration: `collectives/configuration.yaml`
 * deployment: `deployment/`, `Dockerfile`
 * personal data and anonymisation: `collectives/utils/anonymize.py`,
   exports
 * review bot: `.github/workflows/`, `.github/review/`

# Code review

Every PR is reviewed the same way, whoever (human or agent) does it. The
author runs this review on their branch before asking for a review and pastes
the result in the PR; the maintainer starts from it.

## Scope
 * Only report problems in lines added or modified by the diff.
   Pre-existing code is out of scope, unless the change makes it worse or
   depends on it.
 * Do not report a rule on a line carrying a `review-ok` comment for that
   rule, e.g.:
   ```python
   token = db.Column(db.Text, index=True)  # review-ok: DB1 prefix index set in migration
   ```
   The reason is mandatory; a `review-ok` without reason is itself a
   finding. Exceptions that apply to the whole project are listed in
   *Accepted exceptions* below.

## Accepted exceptions
<!-- Project-wide deviations from the rules above, with their reason. -->
None yet.

## Procedure
1. Get the diff of the branch against `master`: `git diff master...HEAD`.
   For a PR not checked out locally, fetch it first
   (`git fetch origin pull/<number>/head:pr-<number>` then
   `git diff master...pr-<number>`). If the PR discussion is available
   (e.g. through `gh pr view <number> --comments`), do not report again
   a point already discussed and accepted there; GitHub access is optional.
2. Run `uvx ruff format --check`, `uvx ruff check` and the test files related
   to the changed code (`uv run pytest tests/<file>`).
3. Check every rule of this document against the diff, reading the
   surrounding code when needed. Also look for bugs, even when no rule
   covers them.
4. Write the result in the format below.

A review only reads and reports: it does not edit code or commit.

## Severity
 * `BLOCKING`: bug, security issue, data loss, or rule violation in a
   sensitive area. Must be fixed before merge.
 * `SHOULD-FIX`: rule violation or defect that should be fixed in this PR.
 * `SUGGESTION`: optional improvement.

## Output format
```
## Review — <PR title>
Verdict: APPROVE | APPROVE WITH COMMENTS | CHANGES REQUESTED
Checks run: ruff format ✓/✗ | ruff check ✓/✗ | tests: <files> ✓/✗
Merge readiness: ready | <what stands in the way: CI, conflicts, migration fork>
Sensitive areas touched: <list, or none>
Findings:
- [BLOCKING] path/to/file.py:42 — DB1 — <problem> — <proposed fix>
- [SUGGESTION] path/to/other.py:10 — NEW — <problem> — <proposed fix>
Questions for maintainers:
- <a product question (PROD rules) the maintainers decide, never the reviewer>
Reading order: <files in the order to read them, for PRs over 400 changed lines>
```
Every finding cites a rule ID, or `NEW` when no rule covers it (a candidate
for a new rule). The verdict is `CHANGES REQUESTED` as soon as there is one
`BLOCKING` finding. The two last blocks appear only when they have content.
