# Automated review for Collectives: agreed spec

Nothing runs on your repository yet. This is how a bot will run the review described in CODING.md on every pull request and keep one public page of what is waiting for whom, so that Noé and Gilles spend their time where a human is needed. Everything below was accepted on 29 Oct 2026, except who owns each sensitive area, which waits for one confirmation.

1 to decide, 5 to know, 4 decided; about 12 minutes.

- Decide: Each sensitive area gets owners taken from who wrote its code, HelloAsso for Noé and Payline for Gilles.
- Decided: The bot asks four questions of every PR, and the new one, "does this serve the clubs?", is answered by PROD1 to PROD5.
- Decided: Six more rules go into CODING.md, because you already ask for them in reviews.
- Decided: The nine model and migration differences are not bugs, and three small changes let a program check DB2.
- Decided: The dashboard goes public on GitHub Pages, and you choose when it starts.
- Know: The review runs on a small runner that works with any model, and Copilot stays as your second opinion.
- Know: A review comment follows your CODING.md format exactly, and stays short when there is nothing to say.
- Know: The dashboard and a pinned issue show the same list of who is needed where.
- Know: A pull request can never make the bot run its code or read a secret.
- Know: We prove it on past PRs before it ever comments on a new one.

## Most PRs merge without a second pair of eyes, and the large ones wait the longest

Of the 596 human PRs merged so far, 450 were merged by their own author, and 106 of the last 120 were never reviewed. Small PRs merge in hours; PRs over 1,000 lines wait about nine days, and outside contributors with large features wait months (#683, #721, #877). Reviews already lean on AI by hand: Gilles pastes Claude's remarks (#943, #938), and Copilot reviewed #868, #881, #927 and #954 when Noé asked it to.

The cost of the gap shows on #930. Gilles approved it on 19 Oct, then added that `.gpx` uploads must be served as attachments or a script inside one could run on the site. Nobody has answered in ten days, and the approval hides the open question.

<details><summary>Evidence</summary>

Read from the GitHub API on 29 Oct 2026: 717 closed PRs (645 merged, 72 closed unmerged, 69 from Dependabot), with their reviews and comments. Review rate by size: 28% under 30 changed lines, 48% from 30 to 200, 65% from 200 to 1,000, 72% above. Median time to merge for reviewed PRs: 37.6 hours; over 1,000 lines: 218 hours.

</details>

## Each sensitive area gets owners taken from who wrote its code, HelloAsso for Noé and Payline for Gilles

**Ask:** Confirm or correct the owners below; the CODEOWNERS file and its test follow your answer.

A `.github/CODEOWNERS` file makes GitHub ask the owners of a file for a review automatically, and, with a branch rule, keeps a PR touching it from merging without them. Owners below are proposed from the git history: who committed to each file. Where both of you wrote a large share, both own it; where one of you wrote nearly all of it, that person does.

| Sensitive area | Owners | Commits (Noé / Gilles) |
|---|---|---|
| HelloAsso payment (`payment_provider/helloasso.py`) | Noé | all HelloAsso work (#943) |
| Payline payment (`payment_provider/payline.py`) | Gilles | 8 / 18 |
| Payment models, routes and API, `utils/payment.py` | Noé and Gilles | 48 / 113 |
| Sign-in routes (`routes/auth/`) | Noé and Gilles | 6 / 9 |
| `models/auth.py`, `utils/access.py` | Noé | 28 / 10 |
| `models/role.py` | Noé and Gilles | 14 / 10 |
| `models/user_group.py` | Gilles | 1 / 19 |
| Migrations | Noé and Gilles | 44 / 54 |
| `configuration.yaml`, `deployment/` | Noé | 18 / 6 |
| `Dockerfile` | Noé and Gilles | 4 / 6 |
| Personal data and anonymisation (`utils/anonymize.py`) | Noé | written by Florent in Oct 2026 |
| The bot's own files (`.github/workflows/`, `.github/review/`) | Noé | new |

<details><summary>Evidence</summary>

`git log --format=%al -- <path>` on the full history of the repository (1,270 commits), read 29 Oct 2026; the HelloAsso and Payline files were moved into `payment_provider/` in one commit, so their history was read with `--follow` and by commit messages mentioning each provider (HelloAsso: jnguiot; Payline: gdaviet 9, jnguiot 3).

</details>

## The bot asks four questions of every PR, and the new one, "does this serve the clubs?", needs rules only you can set

**Ask:** Accept, change or drop PROD1 to PROD5 below, and say whether your output format may gain two lines: a `Questions for maintainers:` block, and a `Reading order:` line for large PRs.

CODING.md covers whether a change is correct and consistent. It does not cover the question you struggle with most: will this feature serve every activity and every club running Collectives, who will maintain it, and should it change the core or sit on top of it. The equipment rental module is the lesson: it shipped, nobody used or tested it, and #927 removed 5,037 lines of it. Its replacement, the Loxya sync in #934, is the opposite pattern: off by default, invisible to the clubs that do not use Loxya, and tested switched off and on.

The model never answers that question for you. It writes the questions, under their own heading so they are not mistaken for defects.

The rules we propose, written to drop into CODING.md:

- **PROD1** A need specific to one activity is met by configuration (an activity type option or a configuration item), not by code written for that activity.
- **PROD2** Collectives is shared by several clubs, and a feature should serve all of them. When only some clubs need it, it is off by default, leaves no trace when off (no menu, route, log or scheduled task), and is tested both off and on (as in #934).
- **PROD3** A new module, data domain or outside integration should name who will maintain it in the PR description (the lesson of #927).
- **PROD4** Prefer an extension point (a setting, a switch, the API, an outside integration) to changing core behaviour. A PR that changes existing behaviour for every user says so in its description and needs a maintainer decision.
- **PROD5** Prefer hot configuration to cold. Anything a club may want to change (texts, thresholds, switches, the club's identifiers on other services) is an item in `collectives/configuration.yaml`, which admins edit from the site without a restart. `config.py` and `instance/config.py`, read once at start-up, keep only what the server needs to start (secret key, database, paths) or what must never be editable from the site.

<details><summary>How the four questions are split between program, model and human</summary>

| Question | A program checks | The model checks | A human decides |
|---|---|---|---|
| Does it serve the clubs? | Whether the PR adds, changes existing behaviour or removes; new models, tables, blueprints, configuration items or outside services; a `*_ENABLED` switch and its default | Who it serves; code written for one activity; whether a setting, a switch or an outside integration would do instead; whether an owner is named | Whether it goes in |
| Is it correct? | Your CI as it is, plus ruff rule `S113` for HTTP calls without timeout (EXT1), a test that secret settings are hidden (SEC2), and new text columns the anonymised export does not scrub | Logic, permissions, data exposure, the bugs your reviews catch (#690, #624, #463) | BLOCKING findings |
| Is it consistent with the code? | Title tag (COM2), a `[FIX]` without a test change (TEST1), `review-ok` without a reason, IDE or debug leftovers (GEN2) | Every CODING.md rule against the diff, citing the rule ID | — |
| Is it easy to review and to keep? | Size, tests and docs touched | A split proposal and a reading order for large PRs | Whether to ask for a split |

</details>

<details><summary>Evidence</summary>

- #927 (8 Sep 2026): "The equipment rental feature (equipment/reservation) was never used: RESERVATION_ENABLED defaulted to false, no test covered it, and its routes stayed reachable by URL even though the navigation links were hidden."
- #934: "Ce code est partagé ; la plupart des clubs n'utilisent pas Loxya. Par défaut, l'intégration ne laisse aucune trace", with `tests/test_loxya_visibility.py` checking each point off then on.
- Closed for product reasons rather than defects: #683 (use the badge system, logic belongs on `User`), #877 (auto-registration undesirable, overlap with other work), #726 (account recovery already covers it).
- Hot configuration: `collectives/configuration.yaml` items are stored in the database (`ConfigurationItem`) and edited from the admin page, with switches such as `PAYMENT_ENABLED`, `REFUND_ENABLED`, `USER_SEARCH_ENABLED`, `ENABLE_SANCTIONS`. Cold configuration: `config.py` says "this file should be modified only by developper. To deploy an application with specific parameters, use instance/config.py".

</details>

## Six more rules are worth writing down, because you already ask for them in reviews

**Ask:** Accept, change or drop each of the six rules below.

The same remarks come back in your and Gilles's reviews, but CODING.md does not hold them yet. Written down, the bot can cite them and contributors can check them before asking. We kept only remarks made on at least two PRs, or one that matters for security.

- **GEN2** One concern per PR. No IDE, personal or debug files (`launch.json`, `.vscode/`, `console.log`, `breakpoint()`). Seen on #598, #663, #693, #546, #611.
- **SEC4** Uploaded documents other than images are served as attachments (`Content-Disposition: attachment`), never rendered by the browser. From Gilles's #930 note on `.gpx`.
- **SEC5** A route acting on one event, user or role checks the rights on that object (for instance `event.has_edit_rights`), not only the user's general role. Seen on #463, #868, #787.
- **PERF1** No database query per item inside a loop: load what the loop needs once. Seen on #529 and #948.
- **UI1** Text shown to users follows French spelling conventions (`événement`, not `évènement`). Seen on #514, #517.
- **UI2** Every page works on a phone: no horizontal scrolling, nothing cut off, buttons and fields usable by touch. Check a new or changed page at phone width before asking for a review. Seen on #423 (front page CSS for mobile), #874 and #731.

<details><summary>Evidence</summary>

- #693 (jnguiot): "Il ne faut pas commiter le launch.json". #598: "on a plutôt l'habitude de faire une PR par feature". #663: "ce changement n'est pas lié aux calendriers". #546: "Ca ressemble à un reste de débug".
- #463 (gdaviet): the route "devrait vérifier les droits de l'utilisateur (`event.has_edit_rights`)". #868: Copilot found a route without `@confidentiality_agreement()`.
- #529 (gdaviet): load the configuration table once rather than one query per variable. #948: the N+1 on `role.user`, fixed by the author.
- #514 (gdaviet): "événement" not "évènement". #517: "Excel avec un seul 'l'".
- #423 "[FIX] Fix front page css for mobile"; #874 "Amélioration de design"; #731 "[FEATURE] New events page using vuejs" (UI and mobile remarks in review).

</details>

## The nine model and migration differences are not bugs, and three small changes let a program check DB2

**Ask:** Say yes or no to the three changes below, in a separate small PR; after it, `flask db check` joins the MariaDB job and a model change without its migration fails CI.

`flask db check` compares the models with what the migrations build and fails if they differ, which is exactly DB2. On `master` it already fails on nine differences, and you are right that the site works: none of them is a bug in production. Two only exist on SQLite (an old foreign key SQLite could not drop, and a stray space in an Enum value). The other seven are places where a model says something slightly different from what the database has had for years: a column the model calls nullable but the database does not, an index the model forgot, a foreign key the model declares but a migration once commented out.

The usual cure, the one Apache Airflow uses, has three parts, none needing a new dependency or a database migration:

1. Run the check only on MariaDB, the production engine, as a last step of the existing migrations job. The SQLite-only noise disappears.
2. Make the models say what production already is: `nullable=False` on `config.type` and `events.event_type_id`; `nullable=True, index=True` on `registrations.registration_time`.
3. List the remaining harmless leftovers as accepted in `migrations/env.py` (Alembic's `include_object` filter): the payments index that kept its old name after a column rename, and the `events.main_leader_id` foreign key that production never had.

After that the accepted list holds three historic items, and anything new fails. Two real fixes are possible but not needed for this: adding the missing foreign key on `events.main_leader_id` (after checking for orphan rows), and back-filling the empty `registration_time` values.

<details><summary>Evidence</summary>

Reproduced on 29 Oct 2026 at commit 49bf908 on SQLite; MariaDB was not run locally (the same check will run in your MariaDB job on our fork). `config.type`: model `collectives/models/configuration.py:217`, column created `nullable=False` in three migrations. `events.event_type_id`: model `collectives/models/event/model.py:185`, migration `3d974e3ecddf` sets `nullable=False, server_default="1"`. `events.main_leader_id`: model `model.py:171` declares the foreign key, the `create_foreign_key` in migration `3ce1483e95a5` is commented out. `group_event_conditions.event_id`: migration `1006bccb75da` drops foreign keys by name, which SQLite does not have. Payments index: column renamed `creditor_id` to `buyer_id` in migration `88f73f88cb1b`, whose comment says MySQL "won't allow us to drop" the index. `registrations.registration_time`: model `nullable=False` (`collectives/models/registration.py:216`), migration `01e5792cdfac` adds it nullable with an index. `users.type`: migration `bf9a9943d273` lists `"UnverifiedLocal "` with a trailing space, which MariaDB strips. Practice: Alembic's autogenerate documentation (`include_object`, comparison limits) and Apache Airflow's `migrations/env.py` and issue 48998, read 29 Oct 2026.

</details>

## The dashboard goes public on GitHub Pages, and you choose when it starts

**Ask:** Confirm a public page at `club-alpin-annecy.github.io/collectives/`, and pick the date to switch it on.

GitHub Pages is not used by this repository (your documentation lives on your own server), so nothing collides. It needs one admin setting: Settings, Pages, source "GitHub Actions". Because the page is public, it states facts and next steps only, never a judgement on a contributor.

## The review runs on a small runner that works with any model, and Copilot stays as your second opinion

A short script calls any model that speaks the OpenAI format: an open-weight one, a paid one, or Claude through an API key. It needs one secret and nothing on another vendor's side, and it can replay old PRs, which the backtest needs. You pick the model and its key at switch-on.

Copilot keeps its place as the reviewer you call by hand. It cannot follow your output format, its comments cannot be checked by a program before they are posted, and it cannot replay old PRs, so it cannot be the main engine. Two cheap improvements: copy the key rules into `.github/copilot-instructions.md` instead of only linking to CODING.md, and, if your seat is the free one GitHub gives open-source maintainers, let a repository rule run it on every non-draft PR.

<details><summary>Evidence</summary>

Read on 29 Oct 2026. Copilot reviewed four PRs, each requested by hand by jnguiot; the repository has no rulesets. GitHub's docs: automatic review is a repository ruleset; instructions are read from the PR's own branch (so a PR can change them for itself); reviews are comments only, with a fixed layout and no model choice; about $0.25 to $10 of AI credits per review depending on the tier. Claude: 25 PRs since January carry "Generated with Claude Code", but nothing runs on GitHub; the Claude Code Action (MIT) was the alternative engine, set aside because it adds an Anthropic account to manage.

</details>

## A review comment follows your CODING.md format exactly, and stays short when there is nothing to say

The bot posts one comment per PR and edits it on every new push, so a PR never collects a pile of bot messages. Before posting, a program removes any finding that does not cite a rule ID from CODING.md (or `NEW`) and a line the PR actually changed, forces CHANGES REQUESTED when a BLOCKING finding remains, and writes the "Checks run" and "Sensitive areas touched" lines itself.

The first comment below is the bot's real output on #962 in a dry run (nothing was posted). The second is written by hand on #948 to show a full comment; its finding is real and checked against the code.

```
## Review — [INTERNAL] Reset the configuration cache before each test
Verdict: APPROVE
Checks run: DB migrations ✓ | Documentation ✓ | Linter ✓ | Tests ✓
Sensitive areas touched: none
Findings: none
```

```
## Review — [FEATURE] Add leaders review page for activity supervisors
Verdict: CHANGES REQUESTED
Checks run: DB migrations ✓ | Documentation ✓ | Linter ✓ | Tests ✓
Sensitive areas touched: authentication, roles and permissions, database migrations
Findings:
- [BLOCKING] collectives/models/role.py:217 — SEC3 — The new free-text `Role.comment` holds remarks about named members, but `_anonymize_free_texts` in collectives/utils/anonymize.py does not scrub it, so anonymised exports would carry these comments — add `roles.comment` to the free texts scrubbed there, with a test in tests/test_anonymize.py.
Questions for maintainers:
- The definition of "inactive" is still open in the discussion (soirées, drafts, collective events only): decide it before merge, or ship and revise?
- `Role.comment` is new personal data, visible only to the activity's supervisors. Does it fit the club's privacy rules as is?
Reading order: collectives/utils/leaders_review.py, the two migrations, the route, the template.
```

## The dashboard and a pinned issue show the same list of who is needed where

Every day a workflow takes one snapshot of the open PRs and renders it twice: a static page on GitHub Pages and the body of one pinned issue, each linking to the other. Editing the issue sends no notification; every Monday the workflow adds one short comment, so each subscriber gets one message a week. No model is involved: it only reports facts, and every PR shows its date and age.

The groups, in this order: where you are needed (only when someone is asked by name, or for a major dependency update); blocks the release (`prioritaire` or a version label); open questions with no reply, including on approved PRs; to review, nobody assigned; waiting for the author; outside contributors with no reply after 7 days; dependency updates ready; approved, not merged. A PR older than a year that nobody has reviewed gets "relancer ou fermer ?".

<details><summary>What it would have shown on 29 Oct 2026 (illustration)</summary>

```
Où on a besoin de vous
  Noé — #970 python-dateutil 2.9 → 3.0 : montée de version majeure, à décider
Bloque la release (v39.0)
  #930, #934, #939, #940, #942, #948
Questions ouvertes sans réponse
  #930 — remarque de gdaviet sans réponse depuis le 19 oct. (.gpx servi en pièce jointe)
À relire — personne n'est désigné
  #962 — ouverte le 19 oct. (10 j)
  #602 — ouverte le 6 févr. 2023 (1361 j) — très ancienne : relancer ou fermer ?
Contributeurs extérieurs sans réponse après 7 jours
  #886 — notifications mail (acapai), ouverte le 30 mars (213 j)
Dépendances prêtes
  #968 certifi, #969 groupe de 4 mises à jour mineures
```

</details>

## A pull request can never make the bot run its code or read a secret

The review workflow runs on `pull_request_target` and checks out only the base branch, so the scripts that run are the ones already merged, never the PR's. The PR's diff and text reach the model as plain text; the model has no tools and cannot act. The review may only read the code and write PR comments; the dashboard may write the one issue and the Pages site. The only secret is the model's API key. The worst a hostile PR can do by hiding instructions in its text is get a misleading comment, and the filter removes any finding that does not point at a real changed line.

Everything lives in `.github/review/` and two workflows, with no new dependency: the scripts use the Python standard library and the `gh` command. Their tests sit in `tests/unit/`, so your existing Tests job runs them, and each one is checked by breaking the code it guards and watching it fail.

## We prove it on past PRs before it ever comments on a new one

1. Backtest: the review runs on 15 closed PRs, each at its state just before the first human review, and its findings are compared with what you or Gilles found. The set covers small fixes merged fast (#912, #442), features merged after changes were requested (#690, #660, #521), large features with several rounds (#463, #497, #640, #655, #943), PRs closed for product reasons (#683, #877, #726), and permission or migration cases (#927, #868). Results stay on our side.
2. Dogfood: the same, dry, on today's open PRs.
3. A live test on our own fork, replaying two or three past PRs as new ones.
4. Then the switch-on list for an admin: Pages, the model key as a repository secret, and the date.

Out of scope: the bot merging, closing or approving anything; per-PR preview environments.

Next: we fold in your comments on this file, finish the build on this branch, and bring the backtest results before anything runs on a real PR.
