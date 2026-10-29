"""Pure helpers of the automated review: CODING.md parsing and PR facts.

Nothing here talks to the network or to GitHub: every function takes text or
plain data and returns plain data, so it is easy to test.
"""

import re

TAGS = ("FEATURE", "FIX", "INTERNAL", "OTHER")
STRAY_PATTERNS = (".vscode/", ".idea/", "launch.json", ".DS_Store")
DEBUG_PATTERNS = ("breakpoint(", "pdb.set_trace", "console.log(")

CONFIGURATION_PATH = "collectives/configuration.yaml"
TESTS_PREFIX = "tests/"
SENSITIVE_HEADING = "# Sensitive areas"
HEADING_PREFIX = "# "
MODELS_PREFIX = "collectives/models/"
ANONYMIZE_PATH = "collectives/utils/anonymize.py"
TEXT_COLUMN_PATTERNS = ("db.Column(db.Text", "db.Column(db.String")
SWITCH_SUFFIX = "_ENABLED"
SWITCH_PREFIX = "ENABLE_"
REMOVAL_RATIO = 3

STATUS_ADDED = "added"
STATUS_REMOVED = "removed"
CHANGE_ADDS = "adds"
CHANGE_REMOVES = "removes"
CHANGE_MODIFIES = "modifies"
TAG_FIX = "FIX"

RULE_ID_RE = re.compile(r"\*\*([A-Z]+\d+)\*\*")
AREA_RE = re.compile(r"^ \* ([^:]+):(.*)$")
BACKTICK_RE = re.compile(r"`([^`]+)`")
HUNK_RE = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
TITLE_TAG_RE = re.compile(r"^\[([A-Z]+)\]")
REVIEW_OK_RE = re.compile(r"review-ok:\s*[A-Z]+\d+\s*$")
CREATE_TABLE_RE = re.compile(r"""op\.create_table\(\s*["']([^"']+)["']""")
CONFIG_ITEM_RE = re.compile(r"^\s{4}([A-Z][A-Z0-9_]+):\s*$")

NEW_FILE_PREFIX = "+++ "
NEW_FILE_B_PREFIX = "+++ b/"
DIFF_HEADER = "diff --git "


def parse_rule_ids(coding_md: str) -> set[str]:
    """Lists the rule IDs of CODING.md.

    Args:
        coding_md: The text of CODING.md.

    Returns:
        Every `**XXX9**` token, e.g. `DB1`.
    """
    return set(RULE_ID_RE.findall(coding_md))


def parse_sensitive_areas(coding_md: str) -> dict[str, list[str]]:
    """Reads the sensitive areas section of CODING.md.

    Args:
        coding_md: The text of CODING.md.

    Returns:
        Area name to the backticked paths of its bullet, in file order.
    """
    areas: dict[str, list[str]] = {}
    in_section = False
    current = None
    for line in coding_md.splitlines():
        if line.startswith(HEADING_PREFIX):
            in_section = line.strip() == SENSITIVE_HEADING
            current = None
            continue
        if not in_section:
            continue
        match = AREA_RE.match(line)
        if match:
            current = match.group(1).strip()
            areas[current] = BACKTICK_RE.findall(match.group(2))
        elif current and line.startswith(" "):
            areas[current].extend(BACKTICK_RE.findall(line))
    return areas


def path_matches(path: str, pattern: str) -> bool:
    """Tells whether a path is covered by a sensitive pattern.

    Args:
        path: A repository path.
        pattern: A directory (ending with `/`, a prefix) or an exact path.

    Returns:
        True when the path matches.
    """
    if pattern.endswith("/"):
        return path.startswith(pattern)
    return path == pattern


def sensitive_areas_touched(paths: list[str], areas: dict) -> list[str]:
    """Lists the sensitive areas touched by some paths.

    Args:
        paths: The changed paths.
        areas: Area name to patterns, as given by `parse_sensitive_areas`.

    Returns:
        The area names, in the order of `areas`, without duplicates.
    """
    return [
        name
        for name, patterns in areas.items()
        if any(path_matches(path, pattern) for path in paths for pattern in patterns)
    ]


def added_line_contents(diff: str) -> list[tuple[str, int, str]]:
    """Parses a unified diff into its added lines.

    Args:
        diff: A unified diff (`diff --git` format).

    Returns:
        A `(path, new line number, text)` tuple per added line. Deleted files
        have none.
    """
    result: list[tuple[str, int, str]] = []
    path = None
    old_left = new_left = new_number = 0
    for line in diff.splitlines():
        if old_left > 0 or new_left > 0:
            if line.startswith("+"):
                if path:
                    result.append((path, new_number, line[1:]))
                new_number += 1
                new_left -= 1
            elif line.startswith("-"):
                old_left -= 1
            elif not line.startswith("\\"):
                new_number += 1
                old_left -= 1
                new_left -= 1
            continue
        hunk = HUNK_RE.match(line)
        if hunk:
            old_left = int(hunk.group(1) or 1)
            new_number = int(hunk.group(2))
            new_left = int(hunk.group(3) or 1)
        elif line.startswith(DIFF_HEADER):
            path = None
        elif line.startswith(NEW_FILE_B_PREFIX):
            path = line[len(NEW_FILE_B_PREFIX) :]
        elif line.startswith(NEW_FILE_PREFIX):
            path = None
    return result


def added_lines(diff: str) -> dict[str, set[int]]:
    """Lists the new-file line numbers of the added lines, per file.

    Args:
        diff: A unified diff.

    Returns:
        Path to the set of added line numbers.
    """
    result: dict[str, set[int]] = {}
    for path, number, _ in added_line_contents(diff):
        result.setdefault(path, set()).add(number)
    return result


def title_tag(title: str) -> str | None:
    """Extracts the leading `[TAG]` of a PR title.

    Args:
        title: The PR title.

    Returns:
        The tag when it is one of `TAGS`, else None.
    """
    match = TITLE_TAG_RE.match(title)
    if match and match.group(1) in TAGS:
        return match.group(1)
    return None


def is_stray(path: str) -> bool:
    """Tells whether a path looks like an IDE or OS leftover.

    Args:
        path: A repository path.

    Returns:
        True when the path matches one of `STRAY_PATTERNS`.
    """
    for pattern in STRAY_PATTERNS:
        if pattern.endswith("/"):
            if path.startswith(pattern) or f"/{pattern}" in path:
                return True
        elif path == pattern or path.endswith(f"/{pattern}"):
            return True
    return False


def change_type(files: list[dict]) -> str:
    """Classifies a PR as adding, removing or modifying code.

    Args:
        files: The changed files, as given to `pr_facts`.

    Returns:
        `adds`, `removes` or `modifies`.
    """
    if not files:
        return CHANGE_MODIFIES
    additions = sum(item["additions"] for item in files)
    deletions = sum(item["deletions"] for item in files)
    if all(item["status"] == STATUS_ADDED for item in files):
        return CHANGE_ADDS
    if (
        all(item["status"] == STATUS_REMOVED for item in files)
        or deletions > REMOVAL_RATIO * additions
    ):
        return CHANGE_REMOVES
    return CHANGE_MODIFIES


def unanonymised_text_columns(
    paths: list[str], contents: list[tuple[str, int, str]]
) -> list[tuple[str, int]]:
    """Finds new free-text model columns the anonymised export may miss.

    Args:
        paths: The changed paths.
        contents: The added lines, as given by `added_line_contents`.

    Returns:
        A `(path, line)` tuple per added Text or String column under
        `collectives/models/`; empty when the PR also changes `anonymize.py`.
    """
    if ANONYMIZE_PATH in paths:
        return []
    return [
        (path, number)
        for path, number, text in contents
        if path.startswith(MODELS_PREFIX)
        and any(pattern in text for pattern in TEXT_COLUMN_PATTERNS)
    ]


def pr_facts(title: str, files: list[dict], diff: str, areas: dict) -> dict:
    """Computes the facts about a PR that the model must not guess.

    Args:
        title: The PR title.
        files: Items with `path`, `status`, `additions` and `deletions`.
        diff: The unified diff of the PR.
        areas: The sensitive areas of CODING.md.

    Returns:
        The facts, keyed as described in the review tools contract.
    """
    paths = [item["path"] for item in files]
    tag = title_tag(title)
    contents = added_line_contents(diff)
    config_items = [
        match.group(1)
        for path, _, text in contents
        if path == CONFIGURATION_PATH and (match := CONFIG_ITEM_RE.match(text))
    ]
    return {
        "size": sum(item["additions"] + item["deletions"] for item in files),
        "sensitive_areas": sensitive_areas_touched(paths, areas),
        "title_tag": tag,
        "fix_without_test": tag == TAG_FIX
        and not any(path.startswith(TESTS_PREFIX) for path in paths),
        "stray_files": [path for path in paths if is_stray(path)],
        "debug_leftovers": [
            (path, number)
            for path, number, text in contents
            if any(pattern in text for pattern in DEBUG_PATTERNS)
        ],
        "review_ok_without_reason": [
            (path, number)
            for path, number, text in contents
            if REVIEW_OK_RE.search(text)
        ],
        "unanonymised_text_columns": unanonymised_text_columns(paths, contents),
        "change_type": change_type(files),
        "new_tables": [
            match.group(1)
            for _, _, text in contents
            if (match := CREATE_TABLE_RE.search(text))
        ],
        "new_config_items": config_items,
        "new_switches": [
            name
            for name in config_items
            if name.endswith(SWITCH_SUFFIX) or name.startswith(SWITCH_PREFIX)
        ],
    }
