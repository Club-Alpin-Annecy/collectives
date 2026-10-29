"""Tests of the automated review tools in `.github/review/`.

The modules are not a package: they are imported by adding their folder to
`sys.path`.
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
    """Imports a module of `.github/review/`.

    Args:
        name: The module name, e.g. `review_lib`.

    Returns:
        The imported module.
    """
    sys.path.insert(0, str(REVIEW_DIR))
    try:
        return importlib.import_module(name)
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
    kept, dropped = bot.filter_findings([first, second], RULE_IDS, ADDED, TEXTS)
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
    kept, dropped = bot.filter_findings([bad, good], RULE_IDS, ADDED, TEXTS)
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


def test_extended_diff_headers_for_added_removed_and_modified(lib):
    """Each status gets the headers git would print, with /dev/null where due."""
    diff = lib.extended_diff(change_files(), 3)
    assert "diff --git a/new.py b/new.py" in diff
    assert "--- /dev/null\n+++ b/new.py" in diff
    assert "diff --git a/gone.py b/gone.py" in diff
    assert "--- a/gone.py\n+++ /dev/null" in diff
    assert "diff --git a/mod.py b/mod.py" in diff
    assert "--- a/mod.py\n+++ b/mod.py" in diff


def test_extended_diff_is_parsed_by_added_lines(lib):
    """Added file and modified file give their added lines; removed file none."""
    added = lib.added_lines(lib.extended_diff(change_files(), 3))
    assert added == {"new.py": {1, 2}, "mod.py": {5, 35}}


def test_extended_diff_context_does_not_change_added_lines(lib):
    """Invariant: more context never changes which lines count as added."""
    wide = lib.extended_diff(change_files(), 20)
    narrow = lib.extended_diff(change_files(), 3)
    assert lib.added_lines(wide) == lib.added_lines(narrow)


def test_extended_diff_wider_context_shows_more_lines(lib):
    """Line 20 is 15 lines from the nearest change: only the wide diff shows it."""
    assert " line 20\n" in lib.extended_diff(change_files(), 20)
    assert " line 20\n" not in lib.extended_diff(change_files(), 3)


NUMBERED_INPUT = """\
diff --git a/a.py b/a.py
index 1111111..2222222 100644
--- a/a.py
+++ b/a.py
@@ -1,3 +1,3 @@
 one
-two
+TWO
 three
"""


def test_number_lines_exact_on_a_small_hunk(lib):
    """Headers are unchanged; context and added lines carry their new number."""
    out = lib.number_lines(NUMBERED_INPUT).splitlines()
    assert out[:5] == NUMBERED_INPUT.splitlines()[:5]
    assert out[5] == "1| one"
    assert out[7] == "2|+TWO"
    assert out[8] == "3| three"
    assert len(out) == 9


def test_number_lines_removed_line_has_no_number(lib):
    """A removed line keeps its text but gets padding instead of a number."""
    removed = lib.number_lines(NUMBERED_INPUT).splitlines()[6]
    assert removed.endswith("|-two")
    assert not any(char.isdigit() for char in removed.split("|")[0])


def test_added_line_texts_maps_new_numbers_to_text_without_plus(lib):
    """Text of each added line, by path and new line number."""
    texts = lib.added_line_texts(MULTI_DIFF)
    assert texts == {
        "a.py": {2: "added2", 12: "new12", 13: "new13"},
        "b.py": {1: "x", 2: "y"},
    }


def test_pr_facts_new_routes_only_under_routes_and_api(lib):
    """Added `.route(` lines count in routes/ and api/ only."""
    routes = [
        "@blueprint.route('/a')",
        "def a(): pass",
        "@blueprint.route('/b', methods=['POST'])",
    ]
    diff = (
        new_files_diff({"collectives/routes/x.py": routes})
        + new_files_diff({"collectives/api/y.py": routes[:1]})
        + new_files_diff({"collectives/utils/z.py": routes[:1]})
    )
    files = [
        file_entry("collectives/routes/x.py"),
        file_entry("collectives/api/y.py"),
        file_entry("collectives/utils/z.py"),
    ]
    assert facts(lib, files=files, diff=diff)["new_routes"] == [
        ("collectives/routes/x.py", 1),
        ("collectives/routes/x.py", 3),
        ("collectives/api/y.py", 1),
    ]


def test_pr_facts_new_routes_empty_without_routes(lib):
    """The key is always present."""
    diff = new_files_diff({"collectives/routes/x.py": ["x = 1"]})
    result = facts(lib, files=[file_entry("collectives/routes/x.py")], diff=diff)
    assert result["new_routes"] == []


# ------------------------------------------------ round 3: reliability (bot)


@pytest.mark.parametrize(
    "evidence",
    [
        "x = compute(value)",
        "x   =  compute(value)",
        "  x = compute(value)\n",
        "if ok: x = compute(value)  # and more",
    ],
    ids=["exact", "other-whitespace", "padded", "quote-longer-than-line"],
)
def test_filter_findings_keeps_matching_evidence(bot, evidence):
    """Evidence equal to, or containing, the added line is accepted."""
    item = finding(evidence=evidence)
    kept, dropped = bot.filter_findings([item], RULE_IDS, ADDED, TEXTS)
    assert kept == [item]
    assert dropped == []


def test_filter_findings_keeps_evidence_contained_in_the_line(bot):
    """A quote of part of the added line is accepted."""
    item = finding(evidence="compute(value)")
    kept, _ = bot.filter_findings([item], RULE_IDS, ADDED, TEXTS)
    assert kept == [item]


@pytest.mark.parametrize(
    "bad",
    [
        finding(evidence="y = other()"),
        finding(evidence=""),
        finding(evidence="   "),
        finding(evidence=None),
        finding(evidence=123),
        {k: v for k, v in VALID_FINDING.items() if k != "evidence"},
    ],
    ids=["other-line", "empty", "blank", "none", "not-a-string", "missing"],
)
def test_filter_findings_drops_bad_evidence(bot, bad):
    """Evidence of another line, empty, malformed or missing: dropped, no raise."""
    good = finding()
    kept, dropped = bot.filter_findings([bad, good], RULE_IDS, ADDED, TEXTS)
    assert kept == [good]
    assert dropped == [bad]


def test_downgrade_blocking_that_relies_on_unseen_code(bot):
    """BLOCKING with a non-empty `relies_on` becomes SHOULD-FIX."""
    item = finding(relies_on="the definition of compute()")
    assert bot.downgrade([item])[0]["severity"] == "SHOULD-FIX"


def test_downgrade_leaves_input_untouched(bot):
    """The list and its dicts are not modified."""
    item = finding(relies_on="somewhere")
    items = [item]
    result = bot.downgrade(items)
    assert item["severity"] == "BLOCKING"
    assert items == [item]
    assert result is not items
    assert result[0] is not item


def test_downgrade_keeps_everything_else(bot):
    """Other severities, and BLOCKING with nothing unseen, are unchanged."""
    items = [
        finding(relies_on=""),
        finding(severity="SHOULD-FIX", relies_on="x"),
        finding(severity="SUGGESTION", relies_on="x"),
    ]
    assert bot.downgrade(items) == items


def test_keep_after_verification_refuted_with_quote_in_file(bot):
    """Refuted and the quote is really in the file: the finding goes."""
    answer = {"verdict": "refuted", "quote": "if  current_time < event.start"}
    assert not bot.keep_after_verification(answer, "a\nif current_time < event.start\n")


def test_keep_after_verification_refuted_with_quote_not_in_file(bot):
    """A refutation that cites nothing real is ignored."""
    answer = {"verdict": "refuted", "quote": "invented line"}
    assert bot.keep_after_verification(answer, "a\nb\n") is True


@pytest.mark.parametrize(
    "answer",
    [
        {"verdict": "unsure", "quote": "a"},
        {"verdict": "confirmed", "quote": "a"},
        {"verdict": "refuted", "quote": ""},
        {"verdict": "refuted"},
        {"verdict": "maybe"},
        {},
        "not a dict",
        None,
    ],
    ids=[
        "unsure",
        "confirmed",
        "refuted-empty-quote",
        "refuted-no-quote",
        "unknown-verdict",
        "empty",
        "string",
        "none",
    ],
)
def test_keep_after_verification_keeps_otherwise(bot, answer):
    """Only a proven refutation removes a finding; anything else keeps it."""
    assert bot.keep_after_verification(answer, "a\nb\n") is True


def test_build_verify_messages_carry_problem_and_file(bot):
    """The verifier sees the claim and the whole file."""
    item = finding(problem="UNIQUE-PROBLEM-TEXT")
    messages = bot.build_verify_messages(item, "FILE-BODY-789\n")
    joined = "\n".join(message["content"] for message in messages)
    assert "UNIQUE-PROBLEM-TEXT" in joined
    assert "FILE-BODY-789" in joined
    assert "refuted" in joined


def test_cap_findings_orders_by_severity_and_limits(bot):
    """Most severe first, stable inside a severity; the rest is returned capped."""
    items = [
        finding(severity="SUGGESTION", problem="s1"),
        finding(severity="SHOULD-FIX", problem="w1"),
        finding(severity="BLOCKING", problem="b1"),
        finding(severity="SUGGESTION", problem="s2"),
        finding(severity="BLOCKING", problem="b2"),
        finding(severity="SHOULD-FIX", problem="w2"),
        finding(severity="SUGGESTION", problem="s3"),
    ]
    kept, capped = bot.cap_findings(items)
    assert [item["problem"] for item in kept] == ["b1", "b2", "w1", "w2", "s1"]
    assert [item["problem"] for item in capped] == ["s2", "s3"]


def test_cap_findings_custom_limit_and_short_list(bot):
    """The limit is respected; fewer findings than the limit are all kept."""
    items = [finding(problem="a"), finding(severity="SUGGESTION", problem="b")]
    kept, capped = bot.cap_findings(items, limit=1)
    assert [item["problem"] for item in kept] == ["a"]
    assert [item["problem"] for item in capped] == ["b"]
    kept, capped = bot.cap_findings(items)
    assert len(kept) == 2
    assert capped == []


def prompt_text(bot, facts=None, **kwargs) -> str:
    """All message contents of `build_messages`, joined."""
    messages = bot.build_messages(
        "rules", "agents", facts or {}, "DIFF", "", "", **kwargs
    )
    return "\n".join(message["content"] for message in messages)


def test_build_messages_mentions_new_routes_and_security_rule(bot):
    """A non-empty `new_routes` fact names the routes and asks for SEC5."""
    full = prompt_text(bot, {"new_routes": [("collectives/routes/x.py", 7)]})
    assert "collectives/routes/x.py" in full
    assert "SEC5" in full
    assert "SEC5" not in prompt_text(bot, {"new_routes": []})


def test_build_messages_output_schema_has_evidence_and_relies_on(bot):
    """The schema the model must follow lists both new fields."""
    text = prompt_text(bot)
    assert "evidence" in text
    assert "relies_on" in text


def test_build_messages_includes_previous_review_only_when_given(bot):
    """The earlier review appears when non-empty, and never otherwise."""
    assert "PREVIOUS-REVIEW-TEXT" in prompt_text(
        bot, previous_review="PREVIOUS-REVIEW-TEXT"
    )
    assert "PREVIOUS-REVIEW-TEXT" not in prompt_text(bot, previous_review="")
    assert "previous review" not in prompt_text(bot).lower()


# ------------------------------------------ round 4: neutralising posted text

MENTION = "`@jnguiot`"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("@jnguiot", MENTION),
        ("thanks @jnguiot for this", f"thanks {MENTION} for this"),
        ("@org/team please", "`@org/team` please"),
        ("cc @a and @b2.", "cc `@a` and `@b2`."),
        ("(@jnguiot)", f"({MENTION})"),
    ],
    ids=["alone", "mid-sentence", "team", "several", "in-parentheses"],
)
def test_neutralize_wraps_mentions(lib, text, expected):
    """A mention at the start or inside a sentence is put in backticks."""
    assert lib.neutralize(text) == expected


def test_neutralize_leaves_email_addresses_alone(lib):
    """Pinned: an `@` glued to a word is an address, which GitHub never notifies."""
    assert lib.neutralize("write to a@b.fr now") == "write to a@b.fr now"


def test_neutralize_does_not_double_backticks(lib):
    """Text already in backticks is left as it is."""
    assert lib.neutralize("ask `@jnguiot` or `https://x.fr/a`") == (
        "ask `@jnguiot` or `https://x.fr/a`"
    )


def test_neutralize_markdown_link_becomes_text_and_backticked_url(lib):
    """The label stays, the destination is shown but not clickable."""
    assert lib.neutralize("see [the doc](https://evil.fr/x) now") == (
        "see the doc `https://evil.fr/x` now"
    )


def test_neutralize_markdown_image_becomes_text_and_backticked_url(lib):
    """An image is not fetched: its alt text and URL are shown as text."""
    assert lib.neutralize("![logo](https://evil.fr/p.png)") == (
        "logo `https://evil.fr/p.png`"
    )


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_neutralize_wraps_bare_urls(lib, scheme):
    """A bare URL is put in backticks."""
    assert lib.neutralize(f"go to {scheme}://evil.fr/a?b=1 please") == (
        f"go to `{scheme}://evil.fr/a?b=1` please"
    )


def test_neutralize_flattens_newlines_and_tabs(lib):
    """Newlines and tabs become single spaces."""
    assert lib.neutralize("a\nb\tc\n\nd") == "a b c d"


def test_neutralize_truncates_with_an_ellipsis(lib):
    """Longer than the limit: cut to the limit, ending with an ellipsis."""
    out = lib.neutralize("x" * 50, limit=10)
    assert len(out) == 10
    assert out.endswith("…")
    assert lib.neutralize("x" * 10, limit=10) == "x" * 10


def test_neutralize_default_limit_is_600(lib):
    """Without argument, 600 characters are kept."""
    assert len(lib.neutralize("x" * 700)) == 600
    assert lib.neutralize("x" * 600) == "x" * 600


@pytest.mark.parametrize("value", [None, 5, ["a"], {"a": 1}])
def test_neutralize_non_string_is_empty(lib, value):
    """Anything but a string gives an empty string."""
    assert lib.neutralize(value) == ""


HOSTILE = "@evil see https://evil.fr/x"
HOSTILE_OUT = "`@evil` see `https://evil.fr/x`"


def test_render_comment_neutralizes_every_model_text(bot):
    """Title, problem, fix, questions and reading order cannot notify or link."""
    kept = [finding(problem=f"P {HOSTILE}", fix=f"F {HOSTILE}")]
    text = bot.render_comment(
        f"T {HOSTILE}",
        "CHANGES REQUESTED",
        "Checks run: none",
        [],
        kept,
        [f"Q {HOSTILE}"],
        [f"R {HOSTILE}"],
    )
    for prefix in "TPFQR":
        assert f"{prefix} {HOSTILE_OUT}" in text
    assert HOSTILE not in text


def test_render_comment_keeps_the_path_as_is(bot):
    """The path is not prose: it is posted unchanged."""
    kept = [finding(path="collectives/a.py")]
    text = bot.render_comment("t", "v", "c", [], kept, [], [])
    assert "- [BLOCKING] collectives/a.py:3 — DB1 — p — f" in text


def test_render_issue_neutralizes_title_and_author(dash):
    """A hostile PR title or author cannot mention or link from the issue."""
    pr = old_pr(number=11, title=f"T {HOSTILE}", author="@octo")
    groups = dash.build_groups([pr], MAINTAINERS, NOW)
    issue = dash.render_issue(groups, "https://x/dash", NOW)
    assert f"T {HOSTILE_OUT}" in issue
    assert "(`@octo`)" in issue
    assert HOSTILE not in issue


def test_render_html_escapes_and_neutralizes_title(dash):
    """HTML is still escaped, and the title is neutralised too."""
    pr = old_pr(number=11, title="<b>@evil</b> https://evil.fr/x")
    groups = dash.build_groups([pr], MAINTAINERS, NOW)
    page = dash.render_html(groups, "https://github.com/o/r/issues/9", NOW)
    assert "<b>@evil" not in page
    assert "&lt;b&gt;`@evil`&lt;/b&gt; `https://evil.fr/x`" in page


# --------------------------------------- round 4: reviewed state (H1), F5, F6

COMMITS = [
    {"sha": "c1", "author_date": "2026-10-01T10:00:00+00:00"},
    {"sha": "c2", "author_date": "2026-10-02T10:00:00+00:00"},
]


def human_review(user="gdaviet", at="2026-10-03T10:00:00+00:00", sha="r-sha") -> dict:
    """A review item as `pick_reviewed_sha` reads it."""
    return {"user": user, "submitted_at": at, "commit_id": sha}


def human_inline(user="gdaviet", at="2026-10-03T10:00:00+00:00", sha="i-sha") -> dict:
    """An inline review comment item as `pick_reviewed_sha` reads it."""
    return {"user": user, "created_at": at, "original_commit_id": sha}


def test_pick_reviewed_sha_earliest_review_beats_later_inline(bot):
    """The review came first: its commit is the one the human looked at."""
    reviews = [human_review(at="2026-10-03T10:00:00+00:00")]
    inline = [human_inline(at="2026-10-04T10:00:00+00:00")]
    assert bot.pick_reviewed_sha("outsider", reviews, inline, COMMITS) == "r-sha"


def test_pick_reviewed_sha_earliest_inline_beats_later_review(bot):
    """The inline comment came first: its original commit is returned."""
    reviews = [human_review(at="2026-10-05T10:00:00+00:00")]
    inline = [human_inline(at="2026-10-03T10:00:00+00:00")]
    assert bot.pick_reviewed_sha("outsider", reviews, inline, COMMITS) == "i-sha"


def test_pick_reviewed_sha_ignores_the_author_and_bots(bot):
    """Only a human other than the author counts, however early."""
    reviews = [
        human_review(user="outsider", at="2026-10-01T00:00:00+00:00", sha="own"),
        human_review(user="copilot[bot]", at="2026-10-01T01:00:00+00:00", sha="bot"),
        human_review(user="gdaviet", at="2026-10-06T00:00:00+00:00", sha="human"),
    ]
    inline = [human_inline(user="dependabot[bot]", at="2026-10-01T02:00:00+00:00")]
    assert bot.pick_reviewed_sha("outsider", reviews, inline, COMMITS) == "human"


def test_pick_reviewed_sha_none_without_human_review_or_comment(bot):
    """Pinned: only own and bot items, or nothing, give None."""
    reviews = [human_review(user="outsider"), human_review(user="x[bot]")]
    assert bot.pick_reviewed_sha("outsider", reviews, [], COMMITS) is None
    assert bot.pick_reviewed_sha("outsider", [], [], COMMITS) is None


GENERIC = "Cette fonctionnalité sert-elle tous les clubs ? (PROD2)"
GENERIC_WORDS = [
    "Is this useful for all clubs?",
    "Qui maintient ce code ?",
    "Who maintains this?",
    "Does it respect PROD3?",
]
SPECIFIC = "Pourquoi garder `Role.comment` en clair ?"


def test_keep_questions_drops_generic_product_questions_without_facts(bot):
    """No supporting fact: product boilerplate goes, specific questions stay."""
    questions = [*GENERIC_WORDS, SPECIFIC, GENERIC]
    assert bot.keep_questions(questions, {}) == [SPECIFIC]


@pytest.mark.parametrize(
    "facts",
    [
        {"new_tables": ["orders"]},
        {"new_config_items": ["MY_SETTING"]},
        {"new_switches": ["ENABLE_THING"]},
        {"new_routes": [("collectives/routes/x.py", 3)]},
        {"change_type": "adds", "size": 201},
    ],
    ids=["tables", "config-items", "switches", "routes", "big-addition"],
)
def test_keep_questions_keeps_generic_ones_with_a_supporting_fact(bot, facts):
    """Each kind of supporting fact, alone, justifies the product questions."""
    questions = [GENERIC, SPECIFIC]
    assert bot.keep_questions(questions, facts) == questions


@pytest.mark.parametrize(
    "facts",
    [
        {"new_tables": [], "new_routes": [], "change_type": "modifies", "size": 900},
        {"change_type": "adds", "size": 200},
    ],
    ids=["empty-facts-big-modification", "small-addition"],
)
def test_keep_questions_facts_that_do_not_support(bot, facts):
    """Empty lists, a big modification or a small addition support nothing."""
    assert bot.keep_questions([GENERIC, SPECIFIC], facts) == [SPECIFIC]


def test_keep_questions_limit_and_order(bot):
    """At most `limit` questions (3 by default), in the original order."""
    questions = [f"specific {n}" for n in range(6)]
    assert bot.keep_questions(questions, {}) == questions[:3]
    assert bot.keep_questions(questions, {}, limit=5) == questions[:5]
    assert bot.keep_questions(questions, {}, limit=1) == questions[:1]


def test_build_messages_asks_for_a_supporting_fact(bot):
    """The prompt tells the model to ask a product question only with a fact."""
    assert "supporting fact" in prompt_text(bot).lower()


def pr_entry(number: int, *files: str) -> dict:
    """An open PR as `overlapping_prs` reads it."""
    return {"number": number, "title": f"PR {number}", "files": list(files)}


def test_overlapping_prs_lists_shared_paths_ordered_by_number(lib):
    """Other PRs sharing a path, with the shared paths, by ascending number."""
    open_prs = [
        pr_entry(30, "b.py", "z.py"),
        pr_entry(10, "a.py", "b.py", "c.py"),
        pr_entry(20, "unrelated.py"),
    ]
    result = lib.overlapping_prs(["a.py", "b.py"], open_prs, 99)
    assert [item["number"] for item in result] == [10, 30]
    assert result[0]["title"] == "PR 10"
    assert sorted(result[0]["shared"]) == ["a.py", "b.py"]
    assert result[1]["shared"] == ["b.py"]


def test_overlapping_prs_excludes_the_own_pr(lib):
    """The PR under review is never its own overlap."""
    open_prs = [pr_entry(5, "a.py"), pr_entry(6, "a.py")]
    result = lib.overlapping_prs(["a.py"], open_prs, 5)
    assert [item["number"] for item in result] == [6]


def test_overlapping_prs_empty_without_overlap(lib):
    """No shared path, or no open PR, gives an empty list."""
    assert lib.overlapping_prs(["a.py"], [pr_entry(1, "b.py")], 9) == []
    assert lib.overlapping_prs(["a.py"], [], 9) == []


def test_build_messages_lists_overlapping_prs_only_when_present(bot):
    """The overlap section appears with its PR and shared path, else not at all."""
    overlaps = [{"number": 886, "title": "OVERLAP-TITLE", "shared": ["x/shared.py"]}]
    full = prompt_text(bot, overlaps=overlaps)
    assert "#886" in full
    assert "OVERLAP-TITLE" in full
    assert "x/shared.py" in full
    assert "OVERLAP-TITLE" not in prompt_text(bot, overlaps=[])
    assert "overlap" not in prompt_text(bot).lower()


# ------------------------------------------------ round 4: outside services (F7)

PYPROJECT_DIFF = """\
diff --git a/pyproject.toml b/pyproject.toml
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -1,7 +1,9 @@
 [project]
 dependencies = [
     "flask>=3",
+    "stripe>=1",
 ]

 [tool.ruff]
+line-length = 88
 select = []
"""


def outside_services(lib, diff: str, *paths: str) -> list[dict]:
    """The `new_outside_services` fact for a diff touching the given paths."""
    files = [file_entry(path) for path in paths]
    return facts(lib, files=files, diff=diff)["new_outside_services"]


def service(path: str, line: int, signal: str) -> dict:
    """One expected item of `new_outside_services`."""
    return {"path": path, "line": line, "signal": signal}


def test_outside_services_network_imports(lib):
    """Each network library import under collectives/ is a signal."""
    path = "collectives/utils/client.py"
    diff = new_files_diff(
        {
            path: [
                "import json",
                "import requests",
                "from zeep import Client",
                "import urllib.request",
            ]
        }
    )
    assert outside_services(lib, diff, path) == [
        service(path, 2, "network library"),
        service(path, 3, "network library"),
        service(path, 4, "network library"),
    ]


def test_outside_services_ignores_network_imports_in_tests_and_docs(lib):
    """Only code under `collectives/` counts, not tests/ or doc/."""
    diff = new_files_diff(
        {
            "tests/unit/test_x.py": ["import requests"],
            "doc/conf.py": ["import requests"],
        }
    )
    assert outside_services(lib, diff, "tests/unit/test_x.py", "doc/conf.py") == []


def test_outside_services_service_settings(lib):
    """Configuration items named like an account or address are signals."""
    diff = new_files_diff(
        {
            CONFIGURATION_PATH: [
                "    LOXYA_URL:",
                "    SMTP_PASSWORD:",
                "    PAGE_TITLE:",
            ]
        }
    )
    assert outside_services(lib, diff, CONFIGURATION_PATH) == [
        service(CONFIGURATION_PATH, 1, "service setting"),
        service(CONFIGURATION_PATH, 2, "service setting"),
    ]


def test_outside_services_new_dependency_only_inside_the_list(lib):
    """An added line in `dependencies = [` counts; one elsewhere does not."""
    assert outside_services(lib, PYPROJECT_DIFF, "pyproject.toml") == [
        service("pyproject.toml", 4, "new dependency")
    ]


def test_outside_services_ordered_by_path_then_line(lib):
    """Items from several files come sorted by path, then by line."""
    diff = (
        new_files_diff({"collectives/z.py": ["import requests"]})
        + PYPROJECT_DIFF
        + new_files_diff(
            {"collectives/a.py": ["x = 1", "import smtplib", "import socket"]}
        )
    )
    result = outside_services(
        lib, diff, "collectives/z.py", "pyproject.toml", "collectives/a.py"
    )
    assert [(item["path"], item["line"]) for item in result] == [
        ("collectives/a.py", 2),
        ("collectives/a.py", 3),
        ("collectives/z.py", 1),
        ("pyproject.toml", 4),
    ]


def test_outside_services_empty_when_none(lib):
    """The key is always present."""
    diff = new_files_diff({"collectives/x.py": ["import json"]})
    assert outside_services(lib, diff, "collectives/x.py") == []


def test_keep_questions_keeps_generic_ones_with_an_outside_service(bot):
    """A new outside service justifies the product questions."""
    questions = [GENERIC, SPECIFIC]
    facts_ = {
        "new_outside_services": [service("collectives/x.py", 1, "network library")]
    }
    assert bot.keep_questions(questions, facts_) == questions
    assert bot.keep_questions(questions, {"new_outside_services": []}) == [SPECIFIC]


def test_build_messages_mentions_outside_service_only_when_present(bot):
    """The prompt names the service and its signal when there is one."""
    item = service("collectives/utils/client.py", 7, "network library")
    full = prompt_text(bot, {"new_outside_services": [item]})
    assert "collectives/utils/client.py" in full
    assert "outside service" in full.lower()
    assert "collectives/utils/client.py" not in prompt_text(
        bot, {"new_outside_services": []}
    )
