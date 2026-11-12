"""Pure helpers of the automated review: CODING.md parsing and PR facts.

Nothing here talks to the network or to GitHub: every function takes text or
plain data and returns plain data, so it is easy to test.
"""

import difflib
import re

TAGS = ("FEATURE", "FIX", "INTERNAL", "OTHER")
STRAY_PATTERNS = (".vscode/", ".idea/", "launch.json", ".DS_Store")
DEBUG_PATTERNS = ("breakpoint(", "pdb.set_trace", "console.log(")

CONFIGURATION_PATH = "collectives/configuration.yaml"
TESTS_PREFIX = "tests/"
SENSITIVE_HEADING = "# Sensitive areas"
HEADING_PREFIX = "# "
ROUTE_PREFIXES = ("collectives/routes/", "collectives/api/")
ROUTE_MARKER = ".route("
DEV_NULL = "/dev/null"
NUMBER_PADDING = "    "
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

NEUTRALIZE_LIMIT = 600
ELLIPSIS = "…"
CODE_SPAN_RE = re.compile(r"(`[^`]*`)")
LINEBREAK_RE = re.compile(r"[\r\n\t]+")
LINK_RE = re.compile(r"!?\[(?P<label>[^\]]*)\]\((?P<target>[^)\s]*)\)")
URL_RE = re.compile(r"https?://[^\s`]+")
MENTION_RE = re.compile(r"(?<![\w`])@[A-Za-z0-9][A-Za-z0-9_-]*(?:/[A-Za-z0-9_-]+)?")
TRAILING_PUNCTUATION = ".,;:!?)]}'\""
NEUTRALIZE_TOKEN_RE = re.compile(
    "|".join(
        f"(?P<{name}>{pattern.pattern})"
        for name, pattern in (
            ("link", LINK_RE),
            ("url", URL_RE),
            ("mention", MENTION_RE),
        )
    )
)
CONFIG_PY_PATH = "config.py"
CONFIG_PY_RE = re.compile(r"^[A-Z][A-Z0-9_]*\s*=")
CONTENT_LINE_RE = re.compile(r"^\s+content:")
CLIENT_TEST_RE = re.compile(r"def test_\w+\(")
SIGNATURE_MAX_LINES = 20
NEW_FILE_MODE = "new file mode"
NEW_FILE_HEADER = "new file mode 100644"
CLIENT_SUFFIX = "client"
MIN_CLIENT_FIXTURES = 2
DOC_SUFFIXES = (".md", ".rst")
SECURITY_WORDS = (
    "vulnérab",
    "vulnerab",
    "faille",
    "xss",
    "injection",
    "cve",
    "exploit",
)
DESCRIPTION_PLACE = "(description)"
INJECTION_RES = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore (all |the )?(previous|above) instructions",
        r"you are (now )?an? (ai|assistant|reviewer)\b",
        r"system prompt",
        r"<!-- *(ai|llm|claude|gpt|copilot)",
        r"approve this (pr|pull request)",
    )
)
MIGRATIONS_PREFIX = "migrations/versions/"
REVISION_RE = re.compile(r"""^revision\s*=\s*["']([^"']+)["']""", re.MULTILINE)
DOWN_REVISION_RE = re.compile(
    r"""^down_revision\s*=\s*["']([^"']+)["']""", re.MULTILINE
)
LOCK_PACKAGE_RE = re.compile(
    r'\[\[package\]\]\s*\nname = "([^"]+)"\s*\nversion = "([^"]+)"'
)
IMPORT_NAME_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)")
PACKAGE_ALIASES = {"yaml": "pyyaml", "jwt": "pyjwt", "dateutil": "python-dateutil"}
CODE_PREFIX = "collectives/"
PYPROJECT_PATH = "pyproject.toml"
DEPENDENCIES_OPENER = "dependencies = ["
NETWORK_LIBRARIES = (
    "requests",
    "httpx",
    "urllib3",
    "aiohttp",
    "zeep",
    "suds",
    "smtplib",
    "ftplib",
    "paramiko",
    "boto3",
    "socket",
)
NETWORK_MODULE = "urllib.request"
SERVICE_WORDS = (
    "URL",
    "HOST",
    "ENDPOINT",
    "API",
    "TOKEN",
    "KEY",
    "SECRET",
    "PASSWORD",
    "LOGIN",
)
SIGNAL_NETWORK = "network library"
SIGNAL_SETTING = "service setting"
SIGNAL_DEPENDENCY = "new dependency"
IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)")
QUOTED_NAME_RE = re.compile(r"""^\s*["'][^"']+["']""")
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


def wrap_token(match: re.Match) -> str:
    """Rewrites one link, URL or mention so GitHub neither links nor notifies.

    Args:
        match: A match of `NEUTRALIZE_TOKEN_RE`.

    Returns:
        The replacement text.
    """
    if match.group("link") is not None:
        text, url = match.group("label").strip(), match.group("target")
        label = NEUTRALIZE_TOKEN_RE.sub(wrap_token, text)
        return f"{label} `{url}`" if label else f"`{url}`"
    token = match.group(0)
    if match.group("url") is not None:
        tail = len(token) - len(token.rstrip(TRAILING_PUNCTUATION))
        core, rest = token[: len(token) - tail], token[len(token) - tail :]
        return f"`{core}`{rest}"
    return f"`{token}`"


def neutralize(text: object, limit: int = NEUTRALIZE_LIMIT) -> str:
    """Makes model or contributor text safe to post in a comment.

    Mentions and URLs go into backticks, links become text plus the backticked
    URL, line breaks become spaces, and the result is cut to `limit` characters.

    Args:
        text: The text; anything but a string gives "".
        limit: The maximum length of the result.

    Returns:
        The neutralised text.
    """
    if not isinstance(text, str):
        return ""
    parts = CODE_SPAN_RE.split(LINEBREAK_RE.sub(" ", text))
    result = "".join(
        part if index % 2 else NEUTRALIZE_TOKEN_RE.sub(wrap_token, part)
        for index, part in enumerate(parts)
    )
    if len(result) <= limit:
        return result
    cut = result[: limit - 1]
    if cut.count("`") % 2:
        cut = cut[:-1] + "`"
    return cut + ELLIPSIS


def overlapping_prs(
    paths: list[str], open_prs: list[dict], own_number: int
) -> list[dict]:
    """Finds the other open PRs that change some of the same files.

    Args:
        paths: The files changed by the PR under review.
        open_prs: Items with `number`, `title` and `files`.
        own_number: The number of the PR under review.

    Returns:
        `number`, `title` and `shared` paths of each overlapping PR, by number.
    """
    result = []
    for item in sorted(open_prs, key=lambda pr: pr["number"]):
        shared = [path for path in paths if path in item["files"]]
        if item["number"] != own_number and shared:
            result.append(
                {"number": item["number"], "title": item["title"], "shared": shared}
            )
    return result


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


def new_side_lines(diff: str) -> list[tuple[str, int, str, bool, bool]]:
    """Parses a unified diff into the lines of the new side of each file.

    Args:
        diff: A unified diff (`diff --git` format).

    Returns:
        A `(path, new line number, text, added, replaces)` tuple per context or
        added line, in diff order. `replaces` is true for an added line that
        takes the place of a removed line of the same change. Deleted files
        have none.
    """
    result: list[tuple[str, int, str, bool, bool]] = []
    path = None
    old_left = new_left = new_number = pending_removed = 0
    in_additions = False
    for line in diff.splitlines():
        if old_left > 0 or new_left > 0:
            if line.startswith("-"):
                old_left -= 1
                if in_additions:
                    pending_removed, in_additions = 0, False
                pending_removed += 1
                continue
            if line.startswith("\\"):
                continue
            added = line.startswith("+")
            replaces = added and pending_removed > 0
            if replaces:
                pending_removed -= 1
            if not added:
                pending_removed, in_additions = 0, False
            else:
                in_additions = True
            if path:
                result.append((path, new_number, line[1:], added, replaces))
            new_number += 1
            new_left -= 1
            if not added:
                old_left -= 1
            continue
        hunk = HUNK_RE.match(line)
        if hunk:
            old_left = int(hunk.group(1) or 1)
            new_number = int(hunk.group(2))
            new_left = int(hunk.group(3) or 1)
            pending_removed, in_additions = 0, False
        elif line.startswith(DIFF_HEADER):
            path = line.rsplit(" b/", 1)[1] if " b/" in line else None
        elif line.startswith(NEW_FILE_B_PREFIX):
            path = line[len(NEW_FILE_B_PREFIX) :]
        elif line.startswith(NEW_FILE_PREFIX):
            path = None
    return result


def added_line_contents(diff: str) -> list[tuple[str, int, str]]:
    """Parses a unified diff into its added lines.

    Args:
        diff: A unified diff (`diff --git` format).

    Returns:
        A `(path, new line number, text)` tuple per added line. Deleted files
        have none.
    """
    return [
        (path, number, text)
        for path, number, text, added, _ in new_side_lines(diff)
        if added
    ]


def new_outside_services(diff: str) -> list[dict]:
    """Finds the traces of a new outside service in a diff.

    Args:
        diff: A unified diff.

    Returns:
        `path`, `line` and `signal` ("network library", "service setting" or
        "new dependency") per added line, ordered by path then line.
    """
    found = []
    in_dependencies = False
    for path, number, text, added, _ in new_side_lines(diff):
        signal = None
        if path == PYPROJECT_PATH:
            if text.strip().startswith(DEPENDENCIES_OPENER):
                in_dependencies = True
            elif text.strip() == "]":
                in_dependencies = False
            elif added and in_dependencies and QUOTED_NAME_RE.match(text):
                signal = SIGNAL_DEPENDENCY
        elif not added:
            continue
        elif path == CONFIGURATION_PATH:
            item = CONFIG_ITEM_RE.match(text)
            if item and any(word in item.group(1) for word in SERVICE_WORDS):
                signal = SIGNAL_SETTING
        elif path.startswith(CODE_PREFIX) and is_network_import(text):
            signal = SIGNAL_NETWORK
        if signal and added:
            found.append({"path": path, "line": number, "signal": signal})
    return sorted(found, key=lambda item: (item["path"], item["line"]))


def is_network_import(text: str) -> bool:
    """Tells whether a line imports a network library.

    Args:
        text: One line of Python code.

    Returns:
        True for an `import X` or `from X import` of `NETWORK_LIBRARIES`.
    """
    match = IMPORT_RE.match(text)
    if not match:
        return False
    module = match.group(1)
    return module.split(".")[0] in NETWORK_LIBRARIES or module.startswith(
        NETWORK_MODULE
    )


def added_line_texts(diff: str) -> dict[str, dict[int, str]]:
    """Lists the text of the added lines, per file and new line number.

    Args:
        diff: A unified diff.

    Returns:
        Path to a mapping of new line number to the line text (no leading `+`).
    """
    result: dict[str, dict[int, str]] = {}
    for path, number, text in added_line_contents(diff):
        result.setdefault(path, {})[number] = text
    return result


def extended_diff(files: list[dict], context: int) -> str:
    """Builds a unified diff with a chosen amount of context.

    Args:
        files: Items with `path`, `status`, `base_text` and `head_text`
            (None when the file does not exist on that side).
        context: Number of unchanged lines shown around each change.

    Returns:
        The diff text, parsable by `added_lines`. Unchanged files are omitted.
    """
    lines: list[str] = []
    for item in files:
        path = item["path"]
        base, head = item["base_text"], item["head_text"]
        body = list(
            difflib.unified_diff(
                (base or "").splitlines(),
                (head or "").splitlines(),
                n=context,
                lineterm="",
            )
        )
        if not body:
            continue
        old_name = DEV_NULL if base is None else f"a/{path}"
        new_name = DEV_NULL if head is None else f"b/{path}"
        lines.append(f"{DIFF_HEADER}a/{path} b/{path}")
        if base is None:
            lines.append(NEW_FILE_HEADER)
        lines.append(f"--- {old_name}")
        lines += [f"+++ {new_name}", *body[2:]]
    return "".join(f"{line}\n" for line in lines)


def number_lines(diff: str) -> str:
    """Prefixes the lines of each hunk with their new-file line number.

    Args:
        diff: A unified diff.

    Returns:
        The diff where context and added lines read `N|<line>` and removed
        lines read `    |<line>`; headers are unchanged.
    """
    out: list[str] = []
    old_left = new_left = new_number = 0
    for line in diff.splitlines():
        if old_left > 0 or new_left > 0:
            if line.startswith("-"):
                old_left -= 1
                out.append(f"{NUMBER_PADDING}|{line}")
            elif line.startswith("\\"):
                out.append(line)
            else:
                out.append(f"{new_number}|{line}")
                new_number += 1
                new_left -= 1
                if not line.startswith("+"):
                    old_left -= 1
            continue
        out.append(line)
        hunk = HUNK_RE.match(line)
        if hunk:
            old_left = int(hunk.group(1) or 1)
            new_number = int(hunk.group(2))
            new_left = int(hunk.group(3) or 1)
    return "\n".join(out) + "\n"


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


def signature_parameters(lines: list[str]) -> list[str] | None:
    """Reads the parameter names of a function signature.

    Args:
        lines: Consecutive lines, the first holding `def name(`.

    Returns:
        The parameter names once the list closes within the lines, else None.
    """
    text = "\n".join(lines)
    start = text.index("(") + 1
    depth, names, current = 1, [], ""
    for char in text[start:]:
        depth += char in "([{"
        depth -= char in ")]}"
        if depth == 0:
            names.append(current)
            return [
                re.split(r"[:=]", name)[0].strip() for name in names if name.strip()
            ]
        if char == "," and depth == 1:
            names.append(current)
            current = ""
        else:
            current += char
    return None


def combined_client_fixtures(
    contents: list[tuple[str, int, str]],
) -> list[tuple[str, int]]:
    """Finds added tests that take two or more `*client` fixtures.

    A signature may span several consecutive added lines.

    Args:
        contents: The added lines, as given by `added_line_contents`.

    Returns:
        A `(path, line)` tuple, at the `def` line, per such test under `tests/`.
    """
    found = []
    for index, (path, number, text) in enumerate(contents):
        if not path.startswith(TESTS_PREFIX) or not CLIENT_TEST_RE.search(text):
            continue
        lines = [text]
        following = contents[index + 1 : index + SIGNATURE_MAX_LINES]
        for offset, (next_path, next_number, next_text) in enumerate(following, 1):
            if next_path != path or next_number != number + offset:
                break
            lines.append(next_text)
        names = signature_parameters(lines) or []
        if sum(name.endswith(CLIENT_SUFFIX) for name in names) >= MIN_CLIENT_FIXTURES:
            found.append((path, number))
    return found


def changed_defaults(diff: str) -> list[tuple[str, int]]:
    """Finds default values that a diff replaces, not adds.

    Args:
        diff: A unified diff.

    Returns:
        A `(path, line)` tuple per added `NAME =` line of `config.py` or
        `content:` line of the configuration file that replaces a removed line.
    """
    found = []
    for path, number, text, _, replaces in new_side_lines(diff):
        if not replaces:
            continue
        if (path == CONFIG_PY_PATH and CONFIG_PY_RE.match(text)) or (
            path == CONFIGURATION_PATH and CONTENT_LINE_RE.match(text)
        ):
            found.append((path, number))
    return found


def security_writeups(contents: list[tuple[str, int, str]]) -> list[str]:
    """Finds documents whose added lines discuss a weakness.

    Args:
        contents: The added lines, as given by `added_line_contents`.

    Returns:
        The `.md` and `.rst` paths with such a line, without duplicates.
    """
    found = []
    for path, _, text in contents:
        lowered = text.lower()
        if (
            path.endswith(DOC_SUFFIXES)
            and path not in found
            and any(word in lowered for word in SECURITY_WORDS)
        ):
            found.append(path)
    return found


def injection_suspects(
    contents: list[tuple[str, int, str]], body: str
) -> list[tuple[str, int]]:
    """Finds text that addresses an AI reviewer instead of a human.

    Args:
        contents: The added lines, as given by `added_line_contents`.
        body: The PR description.

    Returns:
        `(path, line)` per matching added line (once per line), preceded by
        `("(description)", 0)` when the description matches.
    """
    found = []
    if any(pattern.search(body) for pattern in INJECTION_RES):
        found.append((DESCRIPTION_PLACE, 0))
    found += [
        (path, number)
        for path, number, text in contents
        if any(pattern.search(text) for pattern in INJECTION_RES)
    ]
    return found


def migration_children(texts: list[str]) -> dict[str, list[str]]:
    """Maps each migration revision to the revisions that follow it.

    Args:
        texts: The text of each migration file.

    Returns:
        Parent revision to its child revisions. Merge migrations (tuple
        parents) and roots add nothing.
    """
    children: dict[str, list[str]] = {}
    for text in texts:
        revision, parent = REVISION_RE.search(text), DOWN_REVISION_RE.search(text)
        if revision and parent:
            children.setdefault(parent.group(1), []).append(revision.group(1))
    return children


def created_files(diff: str) -> set[str]:
    """Lists the files a diff creates.

    Args:
        diff: A unified diff.

    Returns:
        The paths whose own diff header says `new file mode`.
    """
    created: set[str] = set()
    path = None
    for line in diff.splitlines():
        if line.startswith(DIFF_HEADER):
            path = line.rsplit(" b/", 1)[1] if " b/" in line else None
        elif line.startswith(NEW_FILE_MODE) and path:
            created.add(path)
    return created


def added_migrations(diff: str) -> dict[str, str]:
    """Reads the revisions of the migration files that a diff adds.

    Args:
        diff: A unified diff.

    Returns:
        Revision to down revision, for each migration file the diff creates
        (a modified migration is not a new one) with a single parent.
    """
    created = created_files(diff)
    texts: dict[str, list[str]] = {}
    for path, _, text in added_line_contents(diff):
        if path.startswith(MIGRATIONS_PREFIX) and path in created:
            texts.setdefault(path, []).append(text)
    result = {}
    for lines in texts.values():
        text = "\n".join(lines)
        revision, parent = REVISION_RE.search(text), DOWN_REVISION_RE.search(text)
        if revision and parent:
            result[revision.group(1)] = parent.group(1)
    return result


def migration_forks(
    added: dict[str, str], base_children: dict[str, list[str]]
) -> list[dict]:
    """Finds new migrations that branch the history.

    Args:
        added: Revision to down revision of the migrations the PR adds.
        base_children: Parent to children revisions on the base branch.

    Returns:
        A `revision`, `parent`, `child` dict per added migration whose parent
        already has a child on the base branch.
    """
    forks = []
    for revision, parent in added.items():
        existing = [
            child for child in base_children.get(parent, []) if child not in added
        ]
        if existing:
            forks.append({"revision": revision, "parent": parent, "child": existing[0]})
    return forks


def imported_modules(diff: str) -> list[str]:
    """Lists the top-level modules imported by added Python lines.

    Args:
        diff: A unified diff.

    Returns:
        The module names, without duplicates, in diff order.
    """
    names: list[str] = []
    for path, _, text in added_line_contents(diff):
        match = IMPORT_NAME_RE.match(text)
        if path.endswith(".py") and match and match.group(1) not in names:
            names.append(match.group(1))
    return names


def pinned_versions(import_names: list[str], uv_lock: str) -> dict[str, str]:
    """Looks up the locked version of imported packages.

    Args:
        import_names: Top-level module names, e.g. `yaml`.
        uv_lock: The text of uv.lock.

    Returns:
        Lower-case lock package name to version; standard library and unknown
        names are omitted.
    """
    locked = {
        name.lower().replace("_", "-"): version
        for name, version in LOCK_PACKAGE_RE.findall(uv_lock)
    }
    result = {}
    for name in import_names:
        package = PACKAGE_ALIASES.get(name, name).lower().replace("_", "-")
        if package in locked:
            result[package] = locked[package]
    return result


def pr_facts(
    title: str, files: list[dict], diff: str, areas: dict, body: str = ""
) -> dict:
    """Computes the facts about a PR that the model must not guess.

    Args:
        title: The PR title.
        files: Items with `path`, `status`, `additions` and `deletions`.
        diff: The unified diff of the PR.
        areas: The sensitive areas of CODING.md.
        body: The PR description.

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
        "stray_files": [
            item["path"]
            for item in files
            if item["status"] == STATUS_ADDED and is_stray(item["path"])
        ],
        "combined_client_fixtures": combined_client_fixtures(contents),
        "changed_defaults": changed_defaults(diff),
        "security_writeups": security_writeups(contents),
        "injection_suspects": injection_suspects(contents, body),
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
        "new_routes": [
            (path, number)
            for path, number, text in contents
            if path.startswith(ROUTE_PREFIXES) and ROUTE_MARKER in text
        ],
        "new_outside_services": new_outside_services(diff),
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
