"""Tests that `.github/CODEOWNERS` mirrors the sensitive areas of CODING.md."""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CODEOWNERS_PATH = REPO_ROOT / ".github" / "CODEOWNERS"
CODING_PATH = REPO_ROOT / "CODING.md"
OWNERS = {"@jnguiot", "@gdaviet"}


@pytest.fixture(name="codeowners_rules")
def fixture_codeowners_rules() -> list[list[str]]:
    """Reads the CODEOWNERS rules.

    Returns:
        One list of tokens (path first, then owners) per non-comment line.
        Fails when the file does not exist yet.
    """
    if not CODEOWNERS_PATH.exists():
        pytest.fail(f"{CODEOWNERS_PATH} does not exist yet")
    lines = CODEOWNERS_PATH.read_text(encoding="utf-8").splitlines()
    return [
        line.split()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


@pytest.fixture(name="review_lib")
def fixture_review_lib():
    """Imports `review_lib`, failing (not skipping) while it is not built."""
    sys.path.insert(0, str(REPO_ROOT / ".github" / "review"))
    try:
        import review_lib  # pylint: disable=import-outside-toplevel
    except ModuleNotFoundError:
        pytest.fail("review_lib is not built yet")
    finally:
        sys.path.pop(0)
    return review_lib


def test_every_sensitive_path_has_its_own_rule(codeowners_rules, review_lib):
    """Each path listed in the sensitive areas of CODING.md has a CODEOWNERS line."""
    areas = review_lib.parse_sensitive_areas(CODING_PATH.read_text(encoding="utf-8"))
    expected = {path for paths in areas.values() for path in paths}
    actual = {rule[0].lstrip("/") for rule in codeowners_rules}
    assert expected - actual == set()


def test_codeowners_covers_only_sensitive_paths(codeowners_rules, review_lib):
    """A CODEOWNERS line is a sensitive path or a file inside a sensitive folder."""
    areas = review_lib.parse_sensitive_areas(CODING_PATH.read_text(encoding="utf-8"))
    sensitive = [path for paths in areas.values() for path in paths]
    extra = [
        rule[0]
        for rule in codeowners_rules
        if not any(
            review_lib.path_matches(rule[0].lstrip("/"), path) for path in sensitive
        )
    ]
    assert extra == []


def test_codeowners_paths_start_with_a_slash(codeowners_rules):
    """Every path is anchored at the repository root."""
    assert [rule[0] for rule in codeowners_rules if not rule[0].startswith("/")] == []


def test_every_rule_names_maintainers_only(codeowners_rules):
    """Every line names at least one owner, and only the maintainers."""
    assert codeowners_rules
    assert [
        rule for rule in codeowners_rules if not rule[1:] or not set(rule[1:]) <= OWNERS
    ] == []
