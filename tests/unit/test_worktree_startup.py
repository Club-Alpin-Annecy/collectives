"""Tests for git worktree database resolution and startup scripts."""

import os
import sys
from unittest.mock import patch

from config import _get_git_main_dir, _get_sqlite_db_path
from run import get_upgrade_command


def test_get_upgrade_command_uses_current_python_interpreter():
    """Verify that run.py constructs the migration command using sys.executable."""
    cmd = get_upgrade_command()
    assert cmd == [sys.executable, "-m", "flask", "db", "upgrade"]


def test_get_git_main_dir_with_worktree_gitdir(tmp_path):
    """Verify that _get_git_main_dir detects worktrees and resolves the main repo."""
    main_repo = tmp_path / "main_repo"
    worktree = tmp_path / "worktree"
    main_repo.mkdir()
    worktree.mkdir()

    # Create worktree .git file pointing to main_repo/.git/worktrees/wt1
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {main_repo}/.git/worktrees/wt1\n", encoding="utf-8")

    assert _get_git_main_dir(str(worktree)) == str(main_repo)


def test_get_git_main_dir_without_worktree(tmp_path):
    """Verify that _get_git_main_dir returns root_dir when not a worktree."""
    regular_repo = tmp_path / "repo"
    regular_repo.mkdir()
    (regular_repo / ".git").mkdir()

    assert _get_git_main_dir(str(regular_repo)) == str(regular_repo)


def test_get_sqlite_db_path_reuses_main_repo_db_in_worktree(tmp_path):
    """Verify that in a worktree without a local db, main repo's app.db is used."""
    main_repo = tmp_path / "main_repo"
    worktree = tmp_path / "worktree"
    main_repo.mkdir()
    worktree.mkdir()

    # Create a populated app.db in main_repo
    main_db = main_repo / "app.db"
    main_db.write_text("sqlite-content", encoding="utf-8")

    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {main_repo}/.git/worktrees/wt1\n", encoding="utf-8")

    resolved = _get_sqlite_db_path(str(worktree))
    assert resolved == str(main_db)


def test_get_sqlite_db_path_prefers_local_non_empty_db(tmp_path):
    """Verify that an existing non-empty local app.db in the worktree is preserved."""
    main_repo = tmp_path / "main_repo"
    worktree = tmp_path / "worktree"
    main_repo.mkdir()
    worktree.mkdir()

    main_db = main_repo / "app.db"
    main_db.write_text("main-content", encoding="utf-8")

    local_db = worktree / "app.db"
    local_db.write_text("local-content", encoding="utf-8")

    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {main_repo}/.git/worktrees/wt1\n", encoding="utf-8")

    resolved = _get_sqlite_db_path(str(worktree))
    assert resolved == str(local_db)


def test_get_sqlite_db_path_falls_back_when_main_db_empty_or_missing(tmp_path):
    """Verify that if main repo db is missing or empty, local db path is returned."""
    main_repo = tmp_path / "main_repo"
    worktree = tmp_path / "worktree"
    main_repo.mkdir()
    worktree.mkdir()

    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {main_repo}/.git/worktrees/wt1\n", encoding="utf-8")

    local_db = str(worktree / "app.db")
    # Case 1: main_db does not exist
    assert _get_sqlite_db_path(str(worktree)) == local_db

    # Case 2: main_db exists but has size 0
    main_db = main_repo / "app.db"
    main_db.write_text("", encoding="utf-8")
    assert _get_sqlite_db_path(str(worktree)) == local_db
