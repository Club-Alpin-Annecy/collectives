"""Tests of the automated review tools in `.github/review/`.

The modules are not a package: they are imported by adding their folder to
`sys.path`. While a module does not exist, every test that needs it fails
(it is never skipped).
"""

import importlib
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / ".github" / "review"
CODING_MD = (REPO_ROOT / "CODING.md").read_text(encoding="utf-8")

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
MAINTAINERS = ["jnguiot", "gdaviet"]
CONFIGURATION_PATH = "collectives/configuration.yaml"

AREAS = {
    "payment": ["collectives/models/payment.py", "collectives/utils/payment_provider/"],
    "database migrations": ["migrations/"],
    "deployment": ["deployment/", "Dockerfile"],
}


def load_module(name: str):
    """Imports a module of `.github/review/`, failing if it does not exist.

    Args:
        name: The module name, e.g. `review_lib`.

    Returns:
        The imported module.
    """
    sys.path.insert(0, str(REVIEW_DIR))
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        pytest.fail(f"{name} is not built yet")
    finally:
        sys.path.pop(0)


@pytest.fixture(name="lib")
def fixture_lib():
    """The `review_lib` module."""
    return load_module("review_lib")


@pytest.fixture(name="bot")
def fixture_bot():
    """The `review_bot` module."""
    return load_module("review_bot")


@pytest.fixture(name="dash")
def fixture_dash():
    """The `review_dashboard` module."""
    return load_module("review_dashboard")


def new_files_diff(files: dict[str, list[str]]) -> str:
    """Builds a unified diff where each file is created with the given lines.

    Args:
        files: Mapping of path to the added lines.

    Returns:
        The unified diff text.
    """
    parts = []
    for path, lines in files.items():
        parts.append(
            f"diff --git a/{path} b/{path}\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            f"+++ b/{path}\n"
            f"@@ -0,0 +1,{len(lines)} @@\n" + "".join(f"+{line}\n" for line in lines)
        )
    return "".join(parts)


def file_entry(path: str, status="modified", additions=1, deletions=0) -> dict:
    """Builds one item of the `files` argument of `pr_facts`."""
    return {
        "path": path,
        "status": status,
        "additions": additions,
        "deletions": deletions,
    }


# ---------------------------------------------------------------- review_lib

MULTI_DIFF = """\
diff --git a/a.py b/a.py
index 111..222 100644
--- a/a.py
+++ b/a.py
@@ -1,3 +1,4 @@
 line1
+added2
 line3
 line4
@@ -10,2 +11,3 @@
 ctx
-old
+new12
+new13
diff --git a/b.py b/b.py
new file mode 100644
--- /dev/null
+++ b/b.py
@@ -0,0 +1,2 @@
+x
+y
diff --git a/c.py b/c.py
deleted file mode 100644
--- a/c.py
+++ /dev/null
@@ -1,2 +0,0 @@
-x
-y
"""


def test_parse_rule_ids_on_real_coding_md(lib):
    """All rule IDs of CODING.md are found, and only them."""
    expected = {
        "GEN1",
        "GEN2",
        *(f"PROD{i}" for i in range(1, 6)),
        *(f"PY{i}" for i in range(1, 9)),
        "HTML1",
        "UI1",
        "UI2",
        *(f"ALL{i}" for i in range(1, 4)),
        *(f"DB{i}" for i in range(1, 4)),
        *(f"SEC{i}" for i in range(1, 6)),
        "PERF1",
        "EXT1",
        *(f"TEST{i}" for i in range(1, 4)),
        *(f"COM{i}" for i in range(1, 4)),
    }
    assert lib.parse_rule_ids(CODING_MD) == expected


def test_parse_sensitive_areas_names_and_order(lib):
    """The seven areas come in file order."""
    assert list(lib.parse_sensitive_areas(CODING_MD)) == [
        "payment",
        "authentication, roles and permissions",
        "database migrations",
        "configuration",
        "deployment",
        "personal data and anonymisation",
        "review bot",
    ]


def test_parse_sensitive_areas_paths(lib):
    """Paths come from the backticks, also on continuation lines."""
    areas = lib.parse_sensitive_areas(CODING_MD)
    assert areas["payment"] == [
        "collectives/models/payment.py",
        "collectives/utils/payment.py",
        "collectives/utils/payment_provider/",
        "collectives/routes/payment.py",
        "collectives/api/payment.py",
    ]
    assert areas["authentication, roles and permissions"] == [
        "collectives/routes/auth/",
        "collectives/models/auth.py",
        "collectives/models/role.py",
        "collectives/models/user_group.py",
        "collectives/utils/access.py",
    ]
    assert areas["database migrations"] == ["migrations/"]
    assert areas["configuration"] == ["collectives/configuration.yaml"]
    assert areas["deployment"] == ["deployment/", "Dockerfile"]


def test_parse_sensitive_areas_ignores_words_without_backticks(lib):
    """`exports` is not backticked, so it is not a path."""
    areas = lib.parse_sensitive_areas(CODING_MD)
    assert areas["personal data and anonymisation"] == [
        "collectives/utils/anonymize.py"
    ]


def test_parse_sensitive_areas_stops_at_next_heading(lib):
    """Backticks in the following section are not collected."""
    text = "# Sensitive areas\n\n * one: `a/`\n * two: `b.py`,\n   `c.py`\n\n# Next\n * three: `d.py`\n"
    assert lib.parse_sensitive_areas(text) == {"one": ["a/"], "two": ["b.py", "c.py"]}


@pytest.mark.parametrize(
    "path, pattern, expected",
    [
        ("migrations/versions/x.py", "migrations/", True),
        ("migrations/", "migrations/", True),
        ("src/migrations/x.py", "migrations/", False),
        ("migrationsx/y.py", "migrations/", False),
        ("Dockerfile", "Dockerfile", True),
        ("Dockerfile.dev", "Dockerfile", False),
        ("sub/Dockerfile", "Dockerfile", False),
        ("collectives/utils/payment.py", "collectives/utils/payment.py", True),
        ("collectives/utils/payment.pyc", "collectives/utils/payment.py", False),
    ],
)
def test_path_matches(lib, path, pattern, expected):
    """A directory pattern is a prefix; any other pattern is an exact path."""
    assert lib.path_matches(path, pattern) is expected


def test_sensitive_areas_touched_in_file_order_without_duplicates(lib):
    """Area names follow the order of the areas, not of the paths."""
    paths = [
        "Dockerfile",
        "deployment/run.sh",
        "migrations/versions/a.py",
        "collectives/models/payment.py",
        "README.md",
    ]
    assert lib.sensitive_areas_touched(paths, AREAS) == [
        "payment",
        "database migrations",
        "deployment",
    ]


def test_sensitive_areas_touched_none(lib):
    """Unrelated paths touch nothing."""
    assert lib.sensitive_areas_touched(["README.md"], AREAS) == []


def test_added_lines_multi_file_multi_hunk(lib):
    """New-file line numbers of `+` lines, per file, across hunks."""
    added = lib.added_lines(MULTI_DIFF)
    assert added["a.py"] == {2, 12, 13}
    assert added["b.py"] == {1, 2}


def test_added_lines_omits_deleted_file(lib):
    """A deleted file has no new line."""
    assert "c.py" not in lib.added_lines(MULTI_DIFF)


@pytest.mark.parametrize(
    "title, expected",
    [
        ("[FEATURE] new thing", "FEATURE"),
        ("[FIX] Fixes #1 : bug", "FIX"),
        ("[INTERNAL] refactor", "INTERNAL"),
        ("[OTHER] misc", "OTHER"),
        ("[FIX]no space", "FIX"),
        ("[fix] lowercase", None),
        ("[WIP] unknown tag", None),
        ("FIX without brackets", None),
        ("a [FIX] in the middle", None),
        ("", None),
    ],
)
def test_title_tag(lib, title, expected):
    """Only a leading, upper-case, known `[TAG]` counts."""
    assert lib.title_tag(title) == expected


def facts(lib, title="[INTERNAL] t", files=None, diff="", areas=None) -> dict:
    """Calls `pr_facts` with neutral defaults."""
    return lib.pr_facts(title, files or [], diff, AREAS if areas is None else areas)


def test_pr_facts_size_is_additions_plus_deletions(lib):
    """Size sums both counters over all files."""
    files = [
        file_entry("a.py", additions=3, deletions=1),
        file_entry("b.py", additions=2, deletions=4),
    ]
    assert facts(lib, files=files)["size"] == 10


def test_pr_facts_sensitive_areas_and_title_tag(lib):
    """Both are delegated to the dedicated helpers."""
    result = facts(lib, title="[FIX] x", files=[file_entry("Dockerfile")])
    assert result["sensitive_areas"] == ["deployment"]
    assert result["title_tag"] == "FIX"


@pytest.mark.parametrize(
    "title, paths, expected",
    [
        ("[FIX] x", ["collectives/a.py"], True),
        ("[FIX] x", ["collectives/a.py", "tests/unit/test_a.py"], False),
        ("[FEATURE] x", ["collectives/a.py"], False),
        ("no tag", ["collectives/a.py"], False),
    ],
)
def test_pr_facts_fix_without_test(lib, title, paths, expected):
    """Only a FIX without any file under `tests/` is flagged."""
    files = [file_entry(path) for path in paths]
    assert facts(lib, title=title, files=files)["fix_without_test"] is expected


def test_pr_facts_stray_files(lib):
    """Editor and OS leftovers are listed, in input order."""
    paths = [
        ".vscode/launch.json",
        "collectives/a.py",
        ".idea/workspace.xml",
        "src/launch.json",
        "docs/.DS_Store",
        "sub/.vscode/settings.json",
    ]
    files = [file_entry(path) for path in paths]
    assert facts(lib, files=files)["stray_files"] == [
        ".vscode/launch.json",
        ".idea/workspace.xml",
        "src/launch.json",
        "docs/.DS_Store",
        "sub/.vscode/settings.json",
    ]


def test_pr_facts_debug_leftovers_only_on_added_lines(lib):
    """Debug calls are found with their new line number; removed lines are not."""
    diff = new_files_diff(
        {"a.py": ["x = 1", "breakpoint()", "import pdb; pdb.set_trace()"]}
    ) + (
        "diff --git a/b.py b/b.py\n--- a/b.py\n+++ b/b.py\n"
        "@@ -1,2 +1,2 @@\n-breakpoint()\n+console.log(1)\n ok\n"
    )
    result = facts(lib, files=[file_entry("a.py"), file_entry("b.py")], diff=diff)
    assert result["debug_leftovers"] == [("a.py", 2), ("a.py", 3), ("b.py", 1)]


def test_pr_facts_review_ok_without_reason(lib):
    """A `review-ok: <ID>` followed by nothing is flagged; one with a reason is not."""
    diff = new_files_diff(
        {
            "a.py": [
                "a = 1  # review-ok: DB1",
                "b = 2  # review-ok: DB1 prefix index set in migration",
                "c = 3  # review-ok: PY5   ",
            ]
        }
    )
    result = facts(lib, files=[file_entry("a.py")], diff=diff)
    assert result["review_ok_without_reason"] == [("a.py", 1), ("a.py", 3)]


@pytest.mark.parametrize(
    "entries, expected",
    [
        ([("a.py", "added", 5, 0), ("b.py", "added", 1, 0)], "adds"),
        ([("a.py", "removed", 0, 5), ("b.py", "removed", 0, 1)], "removes"),
        ([("a.py", "modified", 10, 31)], "removes"),
        ([("a.py", "modified", 10, 30)], "modifies"),
        ([("a.py", "added", 5, 0), ("b.py", "modified", 3, 3)], "modifies"),
    ],
)
def test_pr_facts_change_type(lib, entries, expected):
    """Adds, removes (or deletions over 3x additions), else modifies."""
    files = [file_entry(*entry) for entry in entries]
    assert facts(lib, files=files)["change_type"] == expected


def test_pr_facts_new_tables(lib):
    """Table names come from added `op.create_table(` lines, either quote style."""
    diff = new_files_diff(
        {
            "migrations/versions/x.py": [
                '    op.create_table("users",',
                "    op.create_table('orders',",
                '    op.drop_table("old")',
            ]
        }
    )
    result = facts(lib, files=[file_entry("migrations/versions/x.py")], diff=diff)
    assert sorted(result["new_tables"]) == ["orders", "users"]


def test_pr_facts_new_config_items_and_switches(lib):
    """Top-level items of the configuration file; switches are a subset."""
    diff = new_files_diff(
        {
            CONFIGURATION_PATH: [
                "    MY_SETTING:",
                "        content: 1",
                "    MY_FEATURE_ENABLED:",
                "    ENABLE_THING:",
                "    lowercase:",
                "Section:",
            ]
        }
    )
    result = facts(lib, files=[file_entry(CONFIGURATION_PATH)], diff=diff)
    assert sorted(result["new_config_items"]) == [
        "ENABLE_THING",
        "MY_FEATURE_ENABLED",
        "MY_SETTING",
    ]
    assert sorted(result["new_switches"]) == ["ENABLE_THING", "MY_FEATURE_ENABLED"]


MODEL_PATH = "collectives/models/x.py"
ANONYMIZE_PATH = "collectives/utils/anonymize.py"
COLUMNS = [
    "class X:",
    "    a = db.Column(db.Integer)",
    "    b = db.Column(db.Text)",
    "    c = db.Column(db.String(50), nullable=False)",
]


def test_pr_facts_unanonymised_text_columns(lib):
    """Text and String columns of a model are reported with their new line."""
    diff = new_files_diff({MODEL_PATH: COLUMNS})
    result = facts(lib, files=[file_entry(MODEL_PATH)], diff=diff)
    assert result["unanonymised_text_columns"] == [(MODEL_PATH, 3), (MODEL_PATH, 4)]


def test_pr_facts_unanonymised_text_columns_empty_when_anonymize_changes(lib):
    """Touching anonymize.py in the same PR clears the fact."""
    diff = new_files_diff({MODEL_PATH: COLUMNS})
    files = [file_entry(MODEL_PATH), file_entry(ANONYMIZE_PATH)]
    assert facts(lib, files=files, diff=diff)["unanonymised_text_columns"] == []


def test_pr_facts_unanonymised_text_columns_only_in_models(lib):
    """A Text column outside `collectives/models/` is not reported."""
    path = "collectives/utils/x.py"
    diff = new_files_diff({path: COLUMNS})
    result = facts(lib, files=[file_entry(path)], diff=diff)
    assert result["unanonymised_text_columns"] == []


def test_pr_facts_config_items_only_from_configuration_file(lib):
    """The same lines in another file are not configuration items."""
    diff = new_files_diff({"other.yaml": ["    MY_SETTING:"]})
    result = facts(lib, files=[file_entry("other.yaml")], diff=diff)
    assert result["new_config_items"] == []
    assert result["new_switches"] == []


# ---------------------------------------------------------------- review_bot

VALID_FINDING = {
    "severity": "BLOCKING",
    "path": "a.py",
    "line": 3,
    "rule": "DB1",
    "problem": "p",
    "fix": "f",
    "evidence": "x = compute(value)",
    "relies_on": "",
}
RULE_IDS = {"DB1", "PY5"}
ADDED = {"a.py": {3, 4}}
TEXTS = {"a.py": {3: "x = compute(value)", 4: "y = other()"}}


def finding(**changes) -> dict:
    """A valid finding with some fields replaced."""
    return {**VALID_FINDING, **changes}


def test_parse_model_json_bare(bot):
    """A bare JSON object is parsed."""
    text = '{"findings": [], "questions": ["q"], "reading_order": ["a.py"]}'
    assert bot.parse_model_json(text) == {
        "findings": [],
        "questions": ["q"],
        "reading_order": ["a.py"],
    }


def test_parse_model_json_fenced_with_prose(bot):
    """A ```json fence inside prose is unwrapped."""
    text = 'Here it is:\n```json\n{"findings": [{"a": {"b": 1}}]}\n```\nDone.'
    assert bot.parse_model_json(text)["findings"] == [{"a": {"b": 1}}]


def test_parse_model_json_defaults_missing_keys(bot):
    """Missing keys default to empty lists."""
    assert bot.parse_model_json("{}") == {
        "findings": [],
        "questions": [],
        "reading_order": [],
    }


@pytest.mark.parametrize("text", ["", "no json here", "[1, 2]"])
def test_parse_model_json_without_object_raises(bot, text):
    """No JSON object means ValueError."""
    with pytest.raises(ValueError):
        bot.parse_model_json(text)


def test_filter_findings_keeps_valid_and_new_rule(bot):
    """A known rule or NEW, on an added line, is kept in order."""
    first = finding()
    second = finding(rule="NEW", line=4, severity="SUGGESTION", evidence="y = other()")
    kept, dropped = bot.filter_findings([first, second], RULE_IDS, ADDED)
    assert kept == [first, second]
    assert dropped == []


@pytest.mark.parametrize(
    "bad",
    [
        finding(rule="XYZ9"),
        finding(line=99),
        finding(path="other.py"),
        finding(severity="CRITICAL"),
        {"severity": "BLOCKING"},
        finding(line="abc"),
        finding(line=None),
    ],
    ids=[
        "unknown-rule",
        "line-not-added",
        "path-not-in-diff",
        "bad-severity",
        "missing-keys",
        "line-not-int",
        "line-none",
    ],
)
def test_filter_findings_drops_invalid(bot, bad):
    """Invalid findings are dropped without raising, valid ones kept."""
    good = finding()
    kept, dropped = bot.filter_findings([bad, good], RULE_IDS, ADDED)
    assert kept == [good]
    assert dropped == [bad]


@pytest.mark.parametrize(
    "severities, expected",
    [
        (["BLOCKING", "SUGGESTION"], "CHANGES REQUESTED"),
        (["SHOULD-FIX", "SUGGESTION"], "APPROVE WITH COMMENTS"),
        ([], "APPROVE"),
    ],
)
def test_verdict(bot, severities, expected):
    """Blocking wins, any finding comments, none approves."""
    assert bot.verdict([finding(severity=sev) for sev in severities]) == expected


def test_checks_line(bot):
    """One symbol per conclusion, in input order."""
    runs = [
        {"name": "ruff format", "conclusion": "success"},
        {"name": "ruff check", "conclusion": "failure"},
        {"name": "tests", "conclusion": None},
    ]
    assert bot.checks_line(runs) == "Checks run: ruff format ✓ | ruff check ✗ | tests …"


def test_checks_line_empty(bot):
    """No check run is stated explicitly."""
    assert bot.checks_line([]) == "Checks run: none"


def test_render_comment_empty(bot):
    """Without findings: `Findings: none`, no optional lines."""
    text = bot.render_comment("My title", "APPROVE", "Checks run: none", [], [], [], [])
    assert text.rstrip("\n") == (
        "<!-- collectives-review -->\n"
        "## Review — My title\n"
        "Verdict: APPROVE\n"
        "Checks run: none\n"
        "Sensitive areas touched: none\n"
        "Findings: none"
    )


def test_render_comment_full(bot):
    """Findings sorted by severity (stable), then questions and reading order."""
    kept = [
        finding(severity="SUGGESTION", path="c.py", line=1, rule="NEW"),
        finding(path="a.py", line=2, rule="DB1", problem="p1", fix="f1"),
        finding(
            severity="SHOULD-FIX",
            path="b.py",
            line=3,
            rule="PY5",
            problem="p2",
            fix="f2",
        ),
        finding(path="a.py", line=9, rule="SEC1", problem="p3", fix="f3"),
    ]
    text = bot.render_comment(
        "My title",
        "CHANGES REQUESTED",
        "Checks run: ruff check ✓",
        ["payment", "deployment"],
        kept,
        ["Why this?", "And that?"],
        ["a.py", "b.py"],
    )
    assert text.rstrip("\n") == (
        "<!-- collectives-review -->\n"
        "## Review — My title\n"
        "Verdict: CHANGES REQUESTED\n"
        "Checks run: ruff check ✓\n"
        "Sensitive areas touched: payment, deployment\n"
        "Findings:\n"
        "- [BLOCKING] a.py:2 — DB1 — p1 — f1\n"
        "- [BLOCKING] a.py:9 — SEC1 — p3 — f3\n"
        "- [SHOULD-FIX] b.py:3 — PY5 — p2 — f2\n"
        "- [SUGGESTION] c.py:1 — NEW — p — f\n"
        "Questions for maintainers:\n"
        "- Why this?\n"
        "- And that?\n"
        "Reading order: a.py, b.py"
    )


def test_find_own_comment_ignores_human_with_marker(bot):
    """Only the bot's marked comment is ours, even if a human quotes the marker."""
    comments = [
        {"id": 1, "body": f"{bot.MARKER}\nquoted", "user": "a-human"},
        {"id": 2, "body": "bot but no marker", "user": bot.BOT_LOGIN},
        {"id": 3, "body": f"{bot.MARKER}\nreview", "user": bot.BOT_LOGIN},
        {"id": 4, "body": f"{bot.MARKER}\nlater", "user": bot.BOT_LOGIN},
    ]
    assert bot.find_own_comment(comments) == 3


def test_find_own_comment_none(bot):
    """No own comment gives None."""
    assert bot.find_own_comment([{"id": 1, "body": bot.MARKER, "user": "x"}]) is None


def test_build_messages_contains_diff_and_rules(bot):
    """The prompt carries the diff and the rule text."""
    messages = bot.build_messages(
        CODING_MD, "agents", {"size": 1}, "DIFF-BODY-123", "discussion", "brief"
    )
    joined = "\n".join(message["content"] for message in messages)
    assert "DIFF-BODY-123" in joined
    assert "**PY5**" in joined


def test_build_messages_asks_about_unanonymised_columns(bot):
    """Only when the fact is non-empty does the prompt raise the anonymised export."""
    empty = {"unanonymised_text_columns": []}
    full = {"unanonymised_text_columns": [("collectives/models/x.py", 3)]}

    def prompt(facts):
        messages = bot.build_messages("rules", "agents", facts, "DIFF", "", "")
        return "\n".join(message["content"] for message in messages).lower()

    assert "anonymised export" not in prompt(empty)
    assert "anonymised export" in prompt(full)
    assert "collectives/models/x.py" in prompt(full)


# ----------------------------------------------------------- review_dashboard


def make_pr(**changes) -> dict:
    """A snapshot PR from an outside contributor, open for 3 days, untouched."""
    pr = {
        "number": 1,
        "title": "[FEATURE] thing",
        "url": "https://github.com/Club-Alpin-Annecy/collectives/pull/1",
        "author": "outsider",
        "is_draft": False,
        "created_at": "2026-10-26T12:00:00+00:00",
        "labels": [],
        "review_decision": None,
        "reviews": [],
        "maintainer_commented": False,
        "unresolved_threads": [],
        "checks_state": None,
        "is_dependabot": False,
        "bump_type": None,
        "requested_reviewers": [],
    }
    return {**pr, **changes}


def old_pr(**changes) -> dict:
    """A snapshot PR created 8 days before `NOW`."""
    return make_pr(created_at="2026-10-21T12:00:00+00:00", **changes)


def dependabot_pr(bump_type="patch", **changes) -> dict:
    """A dependabot snapshot PR."""
    return make_pr(
        author="dependabot[bot]", is_dependabot=True, bump_type=bump_type, **changes
    )


def test_groups_are_ordered_with_french_titles(dash):
    """The eight groups, in order, with their French titles."""
    assert dict(dash.GROUPS) == {
        "needed": "Où on a besoin de vous",
        "release": "Bloque la release",
        "open_questions": "Questions ouvertes sans réponse",
        "to_review": "À relire — personne n'est désigné",
        "waiting_author": "En attente de l'auteur",
        "outside_no_reply": "Contributeurs extérieurs sans réponse après 7 jours",
        "deps_ready": "Dépendances prêtes",
        "approved_not_merged": "Approuvées non fusionnées",
    }
    assert list(dict(dash.GROUPS)) == [
        "needed",
        "release",
        "open_questions",
        "to_review",
        "waiting_author",
        "outside_no_reply",
        "deps_ready",
        "approved_not_merged",
    ]
    assert dash.ISSUE_MARKER == "<!-- collectives-dashboard -->"
    assert dash.OUTSIDE_DAYS == 7


@pytest.mark.parametrize(
    "labels, expected",
    [
        (["prioritaire"], True),
        (["v0.6"], True),
        (["v12"], True),
        (["bug"], False),
        (["v0.6-rc"], False),
        (["version"], False),
    ],
)
def test_classify_release(dash, labels, expected):
    """`prioritaire` or a `vN.N` label blocks the release."""
    groups = dash.classify(make_pr(labels=labels), MAINTAINERS, NOW)
    assert ("release" in groups) is expected


def test_classify_open_questions_needs_a_reply_from_someone_else(dash):
    """An unresolved thread last answered by another person is open."""
    other = make_pr(unresolved_threads=[{"last_author": "jnguiot", "created_at": "x"}])
    own = make_pr(unresolved_threads=[{"last_author": "outsider", "created_at": "x"}])
    assert "open_questions" in dash.classify(other, MAINTAINERS, NOW)
    assert "open_questions" not in dash.classify(own, MAINTAINERS, NOW)
    assert "open_questions" not in dash.classify(make_pr(), MAINTAINERS, NOW)


def test_classify_waiting_author(dash):
    """Changes requested puts the ball in the author's court."""
    pr = make_pr(review_decision="CHANGES_REQUESTED")
    assert "waiting_author" in dash.classify(pr, MAINTAINERS, NOW)
    assert "waiting_author" not in dash.classify(make_pr(), MAINTAINERS, NOW)


@pytest.mark.parametrize(
    "pr, expected",
    [
        (old_pr(), True),
        (make_pr(), False),
        (old_pr(author="jnguiot"), False),
        (old_pr(reviews=[{"author": "gdaviet", "state": "COMMENTED"}]), False),
        (old_pr(maintainer_commented=True), False),
        (dependabot_pr(created_at="2026-10-01T12:00:00+00:00"), False),
    ],
    ids=[
        "old-outsider",
        "recent",
        "maintainer-author",
        "reviewed",
        "commented",
        "dependabot",
    ],
)
def test_classify_outside_no_reply(dash, pr, expected):
    """An outside PR older than 7 days with no sign of life from the club."""
    assert ("outside_no_reply" in dash.classify(pr, MAINTAINERS, NOW)) is expected


@pytest.mark.parametrize(
    "pr, expected",
    [
        (dependabot_pr("patch", checks_state="SUCCESS"), True),
        (dependabot_pr("minor", checks_state="SUCCESS"), True),
        (dependabot_pr("major", checks_state="SUCCESS"), False),
        (dependabot_pr("patch", checks_state="FAILURE"), False),
        (dependabot_pr("patch", checks_state="PENDING"), False),
        (make_pr(bump_type="patch", checks_state="SUCCESS"), False),
    ],
    ids=["patch", "minor", "major", "failing", "pending", "not-dependabot"],
)
def test_classify_deps_ready(dash, pr, expected):
    """Green patch or minor dependabot bumps are ready."""
    assert ("deps_ready" in dash.classify(pr, MAINTAINERS, NOW)) is expected


def test_classify_approved_not_merged(dash):
    """An approved PR still open is listed."""
    assert "approved_not_merged" in dash.classify(
        make_pr(review_decision="APPROVED"), MAINTAINERS, NOW
    )


def test_classify_needed_follows_needed_by(dash):
    """`needed` is set exactly when someone is needed."""
    requested = make_pr(requested_reviewers=["gdaviet"])
    assert "needed" in dash.classify(requested, MAINTAINERS, NOW)
    assert "needed" not in dash.classify(make_pr(), MAINTAINERS, NOW)
    approved = make_pr(review_decision="APPROVED", requested_reviewers=["gdaviet"])
    assert "needed" not in dash.classify(approved, MAINTAINERS, NOW)


def test_classify_a_pr_can_be_in_several_groups(dash):
    """Release-blocking and waiting for the author at once."""
    pr = make_pr(labels=["prioritaire"], review_decision="CHANGES_REQUESTED")
    assert {"release", "waiting_author"} <= dash.classify(pr, MAINTAINERS, NOW)


def test_classify_draft_is_in_no_group(dash):
    """A draft matches nothing, whatever its labels."""
    pr = old_pr(is_draft=True, labels=["prioritaire"], review_decision="APPROVED")
    assert dash.classify(pr, MAINTAINERS, NOW) == set()


def test_needed_by_draft_is_nobody(dash):
    """Nobody is asked to look at a draft."""
    assert dash.needed_by(make_pr(is_draft=True), MAINTAINERS) == []


def test_needed_by_requested_maintainers_only(dash):
    """Requested reviewers who are maintainers are the ones needed."""
    pr = make_pr(requested_reviewers=["gdaviet", "someone-else"])
    assert dash.needed_by(pr, MAINTAINERS) == ["gdaviet"]


def test_needed_by_nobody_when_nobody_is_requested(dash):
    """No request and no dependabot major: nobody is designated."""
    assert dash.needed_by(make_pr(), MAINTAINERS) == []
    assert dash.needed_by(make_pr(author="jnguiot"), MAINTAINERS) == []


@pytest.mark.parametrize("decision", ["APPROVED", "CHANGES_REQUESTED"])
def test_needed_by_nobody_once_decided(dash, decision):
    """A PR with a decision and no request does not need a maintainer."""
    assert dash.needed_by(make_pr(review_decision=decision), MAINTAINERS) == []


def test_needed_by_dependabot(dash):
    """Patch and minor bumps need nobody; major bumps need every maintainer."""
    assert dash.needed_by(dependabot_pr("patch"), MAINTAINERS) == []
    assert dash.needed_by(dependabot_pr("minor"), MAINTAINERS) == []
    assert dash.needed_by(dependabot_pr("major"), MAINTAINERS) == MAINTAINERS


def review(author: str, state: str) -> dict:
    """A review of a snapshot PR."""
    return {"author": author, "state": state}


def test_decision_explicit_wins(dash):
    """A non-null `review_decision` is returned as is."""
    pr = make_pr(
        review_decision="APPROVED", reviews=[review("gdaviet", "CHANGES_REQUESTED")]
    )
    assert dash.decision(pr) == "APPROVED"


@pytest.mark.parametrize(
    "reviews, expected",
    [
        ([], None),
        ([review("gdaviet", "APPROVED")], "APPROVED"),
        ([review("gdaviet", "COMMENTED")], None),
        ([review("outsider", "APPROVED")], None),
        (
            [review("gdaviet", "CHANGES_REQUESTED"), review("gdaviet", "APPROVED")],
            "APPROVED",
        ),
        (
            [review("gdaviet", "APPROVED"), review("gdaviet", "CHANGES_REQUESTED")],
            "CHANGES_REQUESTED",
        ),
        ([review("gdaviet", "APPROVED"), review("gdaviet", "COMMENTED")], "APPROVED"),
        (
            [review("gdaviet", "APPROVED"), review("jnguiot", "CHANGES_REQUESTED")],
            "CHANGES_REQUESTED",
        ),
        ([review("gdaviet", "APPROVED"), review("jnguiot", "APPROVED")], "APPROVED"),
    ],
    ids=[
        "no-reviews",
        "approved",
        "comment-ignored",
        "author-own-review-ignored",
        "later-approval-replaces-changes",
        "later-changes-replace-approval",
        "later-comment-keeps-approval",
        "any-changes-requested-wins",
        "two-approvals",
    ],
)
def test_decision_derived_from_reviews(dash, reviews, expected):
    """With no explicit decision, each reviewer's last verdict counts."""
    assert dash.decision(make_pr(reviews=reviews)) == expected


def test_classify_uses_the_derived_decision(dash):
    """Approved by reviews only: approved, not to review, not needed."""
    pr = make_pr(
        reviews=[review("gdaviet", "APPROVED")], requested_reviewers=["jnguiot"]
    )
    groups = dash.classify(pr, MAINTAINERS, NOW)
    assert "approved_not_merged" in groups
    assert "to_review" not in groups
    assert "needed" not in groups
    assert dash.needed_by(pr, MAINTAINERS) == []


def test_classify_waiting_author_from_derived_decision(dash):
    """Changes requested by reviews only also waits for the author."""
    pr = make_pr(reviews=[review("gdaviet", "CHANGES_REQUESTED")])
    assert "waiting_author" in dash.classify(pr, MAINTAINERS, NOW)


@pytest.mark.parametrize(
    "pr, expected",
    [
        (make_pr(), True),
        (make_pr(author="jnguiot"), True),
        (make_pr(is_draft=True), False),
        (dependabot_pr("patch"), False),
        (make_pr(review_decision="APPROVED"), False),
        (make_pr(reviews=[review("gdaviet", "CHANGES_REQUESTED")]), False),
        (make_pr(requested_reviewers=["gdaviet"]), False),
        (dependabot_pr("major"), False),
        (old_pr(), False),
        (old_pr(author="jnguiot"), True),
    ],
    ids=[
        "outsider-recent",
        "maintainer-author",
        "draft",
        "dependabot",
        "decided",
        "decided-by-reviews",
        "someone-designated",
        "dependabot-major",
        "outsider-no-reply",
        "old-maintainer-pr",
    ],
)
def test_classify_to_review(dash, pr, expected):
    """To review: nobody designated, no decision, not in another waiting group."""
    assert ("to_review" in dash.classify(pr, MAINTAINERS, NOW)) is expected


def test_outsider_without_reply_is_outside_not_to_review(dash):
    """The two groups never overlap for an outside contributor."""
    groups = dash.classify(old_pr(), MAINTAINERS, NOW)
    assert "outside_no_reply" in groups
    assert "to_review" not in groups


def test_age_text_same_year_has_no_year(dash):
    """Date without year, then the age in days."""
    created = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    assert dash.age_text(created, NOW) == "ouverte le 7 oct. (22 j)"


def test_age_text_other_year_has_the_year(dash):
    """Date with the year when it differs from today's."""
    created = datetime(2023, 2, 6, 12, 0, tzinfo=timezone.utc)
    assert dash.age_text(created, NOW) == "ouverte le 6 févr. 2023 (1361 j)"


def mixed_snapshot() -> list[dict]:
    """A snapshot with a PR for most groups, a draft, and unsorted numbers."""
    return [
        make_pr(
            number=7,
            title="Open question PR",
            unresolved_threads=[{"last_author": "jnguiot", "created_at": "x"}],
        ),
        old_pr(number=1, title="Old outsider PR"),
        make_pr(number=2, title="Approved PR", review_decision="APPROVED"),
        dependabot_pr(number=3, title="Bump patch", checks_state="SUCCESS"),
        make_pr(number=4, title="Release PR", labels=["prioritaire"]),
        make_pr(
            number=5, title="Secret draft title", is_draft=True, labels=["prioritaire"]
        ),
        make_pr(number=6, title="Waiting PR", review_decision="CHANGES_REQUESTED"),
        make_pr(
            number=8,
            title="Fix #945 add partial export",
            created_at="2026-10-07T12:00:00+00:00",
            requested_reviewers=["jnguiot"],
        ),
        make_pr(
            number=9,
            title="Very old PR",
            created_at="2023-02-06T12:00:00+00:00",
            reviews=[review("gdaviet", "APPROVED")],
        ),
        dependabot_pr("major", number=10, title="Bump major"),
    ]


def test_build_groups_shape(dash):
    """Every group is present; numbers ascend; `needed` is keyed by person."""
    groups = dash.build_groups(mixed_snapshot(), MAINTAINERS, NOW)
    assert list(groups) == list(dict(dash.GROUPS))
    assert [pr["number"] for pr in groups["release"]] == [4]
    assert [pr["number"] for pr in groups["approved_not_merged"]] == [2, 9]
    assert isinstance(groups["needed"], dict)
    assert [pr["number"] for pr in groups["needed"]["jnguiot"]] == [8, 10]
    assert [pr["number"] for pr in groups["needed"]["gdaviet"]] == [10]


def test_build_groups_all_keys_present_when_empty(dash):
    """An empty snapshot still has every group."""
    groups = dash.build_groups([], MAINTAINERS, NOW)
    assert list(groups) == list(dict(dash.GROUPS))


def test_render_issue_header_and_titles(dash):
    """Marker first, dashboard link, one French heading per non-empty group."""
    groups = dash.build_groups(mixed_snapshot(), MAINTAINERS, NOW)
    issue = dash.render_issue(groups, "https://example.github.io/dash/", NOW)
    assert issue.startswith(dash.ISSUE_MARKER)
    assert "https://example.github.io/dash/" in issue
    assert "## Bloque la release" in issue
    assert "## Approuvées non fusionnées" in issue
    assert "Old outsider PR" in issue
    only_release = dash.build_groups(
        [make_pr(labels=["prioritaire"])], MAINTAINERS, NOW
    )
    assert "## Dépendances prêtes" not in dash.render_issue(only_release, "u", NOW)


def issue_sections(issue: str, dash) -> dict[str, set[int]]:
    """PR numbers listed under each group heading of the issue text.

    Numbers are read from `[#N](` links only: titles may contain `#945`.
    """
    key_by_title = {title: key for key, title in dict(dash.GROUPS).items()}
    sections: dict[str, set[int]] = {}
    current = None
    for line in issue.splitlines():
        if line.startswith("## "):
            current = key_by_title.get(line[3:].strip())
            if current:
                sections[current] = set()
        elif current:
            sections[current].update(int(n) for n in re.findall(r"\[#(\d+)\]\(", line))
    return sections


class DataAttributes(HTMLParser):
    """Collects (data-group, data-pr) pairs of every tag carrying both."""

    def __init__(self):
        super().__init__()
        self.pairs: list[tuple[str, int]] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "data-group" in attributes and "data-pr" in attributes:
            self.pairs.append((attributes["data-group"], int(attributes["data-pr"])))


def test_issue_and_html_list_the_same_prs_per_group(dash):
    """Sync invariant: both outputs agree, group by group."""
    groups = dash.build_groups(mixed_snapshot(), MAINTAINERS, NOW)
    issue = issue_sections(dash.render_issue(groups, "https://x/dash", NOW), dash)
    parser = DataAttributes()
    parser.feed(dash.render_html(groups, "https://github.com/o/r/issues/9", NOW))
    in_html: dict[str, set[int]] = {}
    for group, number in parser.pairs:
        in_html.setdefault(group, set()).add(number)
    non_empty = {key for key in dict(dash.GROUPS) if in_html.get(key) or issue.get(key)}
    assert non_empty
    for key in non_empty:
        assert issue.get(key, set()) == in_html.get(key, set()), key


def test_renderers_show_the_age_text(dash):
    """Both outputs carry the age of a PR, with the year when it is not this year."""
    groups = dash.build_groups(mixed_snapshot(), MAINTAINERS, NOW)
    issue = dash.render_issue(groups, "https://x/dash", NOW)
    page = dash.render_html(groups, "https://github.com/o/r/issues/9", NOW)
    for text in ("ouverte le 7 oct. (22 j)", "ouverte le 6 févr. 2023 (1361 j)"):
        assert text in issue
        assert text in page


def test_drafts_appear_nowhere(dash):
    """A draft is absent from the issue and the page."""
    groups = dash.build_groups(mixed_snapshot(), MAINTAINERS, NOW)
    issue = dash.render_issue(groups, "https://x/dash", NOW)
    page = dash.render_html(groups, "https://github.com/o/r/issues/9", NOW)
    assert "Secret draft title" not in issue + page
    assert 'data-pr="5"' not in page
    assert not re.search(r"#5\b", issue)


def test_render_html_is_self_contained(dash):
    """Only github.com is linked, and the issue link is present."""
    groups = dash.build_groups(mixed_snapshot(), MAINTAINERS, NOW)
    page = dash.render_html(groups, "https://github.com/o/r/issues/9", NOW)
    assert "https://github.com/o/r/issues/9" in page
    hosts = {
        urlparse(url).hostname for url in re.findall(r"https?://[^\s\"'<>]+", page)
    }
    assert hosts <= {"github.com"}


# ------------------------------------------------- round 3: reliability (lib)


def text_of(lines: list[str]) -> str:
    """Joins lines into a file text ending with a newline."""
    return "".join(f"{line}\n" for line in lines)


BASE_LINES = [f"line {n}" for n in range(1, 41)]
HEAD_LINES = [
    "CHANGED 5" if text == "line 5" else "CHANGED 35" if text == "line 35" else text
    for text in BASE_LINES
]


def change_files() -> list[dict]:
    """An added file, a removed file and a modified file with two distant changes."""
    return [
        {
            "path": "new.py",
            "status": "added",
            "base_text": None,
            "head_text": text_of(["n1", "n2"]),
        },
        {
            "path": "gone.py",
            "status": "removed",
            "base_text": text_of(["g1", "g2"]),
            "head_text": None,
        },
        {
            "path": "mod.py",
            "status": "modified",
            "base_text": text_of(BASE_LINES),
            "head_text": text_of(HEAD_LINES),
        },
    ]


NUMBERED_INPUT = """\
diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,3 +1,3 @@
 one
-two
+TWO
 three
"""


# ------------------------------------------------ round 3: reliability (bot)


def prompt_text(bot, facts=None, **kwargs) -> str:
    """All message contents of `build_messages`, joined."""
    messages = bot.build_messages(
        "rules", "agents", facts or {}, "DIFF", "", "", **kwargs
    )
    return "\n".join(message["content"] for message in messages)
