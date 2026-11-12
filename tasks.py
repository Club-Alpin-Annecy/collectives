#! /usr/bin/env python3
"""Development task runner for the project.

    ./tasks.py start        # runs a task; ./tasks.py alone lists the tasks

Development tooling only: it is not included in the installed package.

Worktrees: tasks detect whether they run in a git worktree (rather than in the main
clone). In that case, before starting, they generate the local (git-ignored) file that
isolates the worktree:

  - ``.env``: shifts the published (application) port deterministically from the branch
    name, to coexist with the main checkout and the other worktrees, and points
    ``SQLALCHEMY_DATABASE_URI`` to a database specific to the worktree.

The ``start`` task also seeds the database by copying the one of the main checkout,
which avoids regenerating the test data set. As a result, ``./tasks.py start`` works the
same in the main clone and in a worktree.

Environment variables:
  WORKTREE_SEED_DB=0    disables copying the database of the main checkout
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent

APP_PORT_BASE = 5000
"""Application port in the main clone; a worktree adds its offset to it."""

ENV_BEGIN = "# >>> tasks.py worktree (généré, ne pas committer) >>>"
ENV_END = "# <<< tasks.py worktree <<<"

ENV_HEADER = """# Environnement de développement local — généré par ./tasks.py, non versionné.
#
# Le bloc balisé ci-dessous est réécrit à chaque « ./tasks.py start ». Tout ce qui est
# ajouté APRÈS ce bloc est conservé et prend le pas : c'est l'endroit où placer ses
# réglages personnels.
"""


# ——————————————————————————————————————————————————————————————————————————————
#  Execution helpers
# ——————————————————————————————————————————————————————————————————————————————


def capture(command: str, on_failure: str = None) -> str:
    """Run a command and return its standard output, without displaying it.

    :param command: shell command
    :param on_failure: value returned on failure; if None, the failure is raised
    """
    try:
        done = subprocess.run(
            command, shell=True, cwd=ROOT, capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError:
        if on_failure is None:
            raise
        return on_failure
    return done.stdout.strip()


def run(command: list, env: dict = None, check: bool = True) -> int:
    """Run a command, letting its output be displayed."""
    merged = {**os.environ, **(env or {})}
    return subprocess.run(command, cwd=ROOT, env=merged, check=check).returncode


def info(message: str):
    """Print an information line."""
    print(f"  {message}")


def section(title: str):
    """Print a section title."""
    print(f"\n\033[1m{title}\033[0m")


# ——————————————————————————————————————————————————————————————————————————————
#  Worktree context
# ——————————————————————————————————————————————————————————————————————————————


def worktree_context() -> dict:
    """Isolation context of the current worktree, or None in the main clone.

    The port offset is derived from the branch name: two worktrees get distinct ports
    without any convention to maintain by hand.
    """
    root = Path(capture("git rev-parse --show-toplevel")).resolve()
    common_dir = Path(capture("git rev-parse --git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    main_root = common_dir.parent.resolve()

    branch = capture("git rev-parse --abbrev-ref HEAD")
    # Deterministic offset (5..404), so as not to reuse port 5000 of the main clone.
    offset = zlib.crc32(branch.encode()) % 400 + 5

    if root == main_root:
        return None

    return {
        "branch": branch,
        "slug": re.sub(r"[^A-Za-z0-9]+", "-", branch).strip("-").lower(),
        "offset": offset,
        "app_port": APP_PORT_BASE + offset,
        "root": root,
        "main_root": main_root,
    }


def ports() -> dict:
    """Ports and paths of the current checkout, worktree or not."""
    ctx = worktree_context()
    if ctx is None:
        return {
            "app_port": APP_PORT_BASE,
            "db": ROOT / "app.db",
            "worktree": None,
        }
    return {
        "app_port": ctx["app_port"],
        "db": ROOT / f"collectives-{ctx['slug']}.db",
        "worktree": ctx,
    }


# ——————————————————————————————————————————————————————————————————————————————
#  Local files generation
# ——————————————————————————————————————————————————————————————————————————————


def upsert_env(path: Path, variables: dict):
    """Insert or update a delimited block in a .env file, leaving the rest untouched.

    What is written outside the block (personal settings, real credentials) survives
    regenerations.
    """
    block = "\n".join([ENV_BEGIN, *[f"{k}={v}" for k, v in variables.items()], ENV_END])
    existing = path.read_text(encoding="utf-8") if path.is_file() else ENV_HEADER
    pattern = re.compile(re.escape(ENV_BEGIN) + ".*?" + re.escape(ENV_END), re.DOTALL)

    if pattern.search(existing):
        content = pattern.sub(block, existing)
    else:
        head = existing.rstrip()
        content = (head + "\n\n" if head else "") + block + "\n"

    path.write_text(content, encoding="utf-8")


def write_worktree_files(state: dict):
    """Write the local (git-ignored) file that isolates the current checkout."""
    db = state["db"]

    upsert_env(
        ROOT / ".env",
        {
            "COLLECTIVES_PORT": state["app_port"],
            # The path MUST be absolute: `flask db upgrade` resolves relative sqlite
            # paths from the current directory, while Flask-SQLAlchemy resolves them
            # from instance/, so a relative path creates two databases.
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db}",
            # Without this, the application queries the real FFCAM extranet at first login.
            "EXTRANET_DISABLE": 1,
            # Scheduled tasks must not fire on their own in development.
            "SCHEDULER_ENABLED": "false",
            "FLASK_DEBUG": 1,
            "SECRET_KEY": "dev-only-not-a-real-secret",
            "ADMINPWD": "foobar2",
        },
    )
    info("Fichier d'isolation généré : .env")


def load_env() -> dict:
    """Read .env and return its variables, without depending on python-dotenv."""
    path = ROOT / ".env"
    if not path.is_file():
        return {}

    variables = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        variables[key.strip()] = value.strip()
    return variables


def app_env(**overrides) -> dict:
    """Runtime environment of the application: .env plus FLASK_APP."""
    return {
        **load_env(),
        "FLASK_APP": "collectives:create_app",
        **{k: str(v) for k, v in overrides.items()},
    }


# ——————————————————————————————————————————————————————————————————————————————
#  Bootstrap
# ——————————————————————————————————————————————————————————————————————————————


def ensure_venv():
    """Install the dependencies if the virtualenv of the checkout is missing."""
    if not (ROOT / ".venv").is_dir():
        info("Création du virtualenv (uv sync)…")
        run(["uv", "sync"])


def seed_database(state: dict):
    """Seed the worktree database by copying the one of the main checkout.

    Avoids regenerating the test data set. Idempotent: does nothing if the database
    already exists. Migrations specific to the branch are then applied by
    ``flask db upgrade``.
    """
    ctx = state["worktree"]
    if ctx is None or state["db"].exists():
        return

    if os.environ.get("WORKTREE_SEED_DB") == "0":
        info("Amorçage de la base désactivé (WORKTREE_SEED_DB=0).")
        return

    source = ctx["main_root"] / "app.db"
    if not source.is_file():
        info(f"Amorçage ignoré : {source} introuvable — la base sera créée vide.")
        return

    shutil.copy2(source, state["db"])
    info(f"Base amorcée depuis {source}.")


# ——————————————————————————————————————————————————————————————————————————————
#  Tasks
# ——————————————————————————————————————————————————————————————————————————————

TASKS = {}


def task(name: str, description: str):
    """Declare a task exposed on the command line."""

    def register(function):
        TASKS[name] = (function, description)
        return function

    return register


@task("info", "Affiche les ports, la base et le contexte du checkout courant")
def task_info(_args):
    """Print the isolation context."""
    state = ports()
    ctx = state["worktree"]

    if ctx is None:
        section("Clone principal")
    else:
        section(f"Worktree isolé : {ctx['branch']} (offset +{ctx['offset']})")

    info(f"Application  : http://localhost:{state['app_port']}")
    info(
        f"Base         : {state['db']}"
        + ("" if state["db"].exists() else "  (absente)")
    )
    return 0


@task("start", "Génère l'isolation, amorce et migre la base, démarre l'application")
def task_start(_args):
    """Start the application, isolating the worktree automatically."""
    state = ports()
    task_info(None)

    ensure_venv()
    write_worktree_files(state)
    seed_database(state)

    run(["uv", "run", "flask", "db", "upgrade"], env=app_env())
    section(f"→ http://localhost:{state['app_port']}")
    return run(
        ["uv", "run", "flask", "run", "--port", str(state["app_port"]), "--debug"],
        env=app_env(),
        check=False,
    )


@task("fixtures", "Recharge le jeu de données de test dans la base courante")
def task_fixtures(_args):
    """Regenerate the test data set."""
    run(["uv", "run", "flask", "db", "upgrade"], env=app_env())
    return run(["uv", "run", "python", "etc/test_set.py"], env=app_env(), check=False)


@task("test", "Lance la suite de tests, dans un environnement hermétique")
def task_test(args):
    """Run pytest without the development variables.

    The suite must run as in CI: neither the development database nor the variables
    that disable services; tests have their own mocks in tests/mock/.
    """
    clean = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SQLALCHEMY_", "EXTRANET_", "SCHEDULER_"))
    }
    return subprocess.run(
        ["uv", "run", "pytest", *args.rest], cwd=ROOT, env=clean, check=False
    ).returncode


@task("lint", "Formate le code et lance le linter, comme la CI")
def task_lint(_args):
    """Format then lint the code."""
    run(["uvx", "ruff", "format"], check=False)
    return run(["uvx", "ruff", "check", "--fix"], check=False)


@task("shell", "Shell Python avec le contexte applicatif")
def task_shell(_args):
    """Open a Flask shell."""
    return run(["uv", "run", "flask", "shell"], env=app_env(), check=False)


@task("destroy", "Supprime la base du checkout courant")
def task_destroy(_args):
    """Delete the database, after confirmation in the main clone."""
    state = ports()

    if state["worktree"] is None:
        answer = input("Clone principal détecté : supprimer app.db ? [y/N] ")
        if answer.strip().lower() not in ("y", "o", "yes", "oui"):
            info("Annulé.")
            return 0

    if state["db"].exists():
        state["db"].unlink()
        info(f"Base supprimée : {state['db']}")
    else:
        info("Aucune base à supprimer.")
    return 0


def main() -> int:
    """Entry point: parse the arguments and run the requested task."""
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Tâches :\n"
        + "\n".join(f"  {name:<10} {desc}" for name, (_, desc) in TASKS.items()),
    )
    parser.add_argument("task", nargs="?", choices=list(TASKS), help="tâche à exécuter")
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="arguments transmis")
    args = parser.parse_args()

    if args.task is None:
        parser.print_help()
        return 0

    return TASKS[args.task][0](args) or 0


if __name__ == "__main__":
    sys.exit(main())
