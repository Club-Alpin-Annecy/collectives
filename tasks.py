#! /usr/bin/env python3
"""Automatisation des tâches du projet.

Deux façons de lancer une tâche, au choix :

    uv run start            # points d'entrée déclarés dans pyproject.toml
    ./tasks.py start        # invocation directe ; ./tasks.py seul liste les tâches

``uv run`` a l'avantage de créer et synchroniser le virtualenv au passage.

La suite de tests se lance par ``uv run pytest`` : elle n'a pas de point d'entrée dédié,
une commande nommée « test » entrerait en conflit avec ``/usr/bin/test``. Elle est
hermétique par construction, rien ne chargeant ``.env`` automatiquement — sauf si vous
l'avez sourcé vous-même, auquel cas ``./tasks.py test`` purge les variables de
développement.

Particularité worktree : les tâches détectent si l'on est dans un git worktree (et non
dans le clone principal). Dans ce cas elles génèrent automatiquement, avant de démarrer,
le fichier local (gitignoré) qui isole le worktree :

  - ``.env`` : décale les ports publiés (application, faux serveur Loxya) de façon
    déterministe à partir du nom de branche, pour cohabiter avec le checkout principal
    et les autres worktrees, et pointe ``SQLALCHEMY_DATABASE_URI`` vers une base propre
    au worktree.

La tâche ``start`` amorce aussi la base par copie de celle du checkout principal, ce qui
évite de régénérer le jeu de test. Résultat : ``./tasks.py start`` est transparent, que
l'on soit dans le clone principal ou dans un worktree.

Variables d'environnement :
  WORKTREE_SEED_DB=0    désactive la copie de la base du checkout principal
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
STUB_PORT_BASE = 5500
"""Bases de ports espacées de plus de 400 (l'amplitude de l'offset) pour que les plages
de deux services ne se recouvrent jamais."""

ENV_BEGIN = "# >>> tasks.py worktree (généré, ne pas committer) >>>"
ENV_END = "# <<< tasks.py worktree <<<"

ENV_HEADER = """# Environnement de développement local — généré par ./tasks.py, non versionné.
#
# Le bloc balisé ci-dessous est réécrit à chaque « ./tasks.py start ». Tout ce qui est
# ajouté APRÈS ce bloc est conservé et prend le pas : c'est l'endroit où placer ses
# réglages personnels, par exemple de vrais identifiants Loxya de recette.
"""


# ——————————————————————————————————————————————————————————————————————————————
#  Helpers d'exécution
# ——————————————————————————————————————————————————————————————————————————————


def capture(command: str, on_failure: str = None) -> str:
    """Exécute une commande et renvoie sa sortie standard, sans l'afficher.

    :param command: commande shell
    :param on_failure: valeur renvoyée en cas d'échec ; si None, l'échec est propagé
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
    """Exécute une commande en laissant sa sortie s'afficher."""
    merged = {**os.environ, **(env or {})}
    return subprocess.run(command, cwd=ROOT, env=merged, check=check).returncode


def probe(command: str) -> bool:
    """Sonde silencieuse et tolérante à l'échec : renvoie True si la commande réussit."""
    return (
        subprocess.run(
            command, shell=True, cwd=ROOT, capture_output=True
        ).returncode
        == 0
    )


def info(message: str):
    """Affiche une ligne d'information."""
    print(f"  {message}")


def section(title: str):
    """Affiche un titre de section."""
    print(f"\n\033[1m{title}\033[0m")


# ——————————————————————————————————————————————————————————————————————————————
#  Contexte worktree
# ——————————————————————————————————————————————————————————————————————————————


def worktree_context() -> dict:
    """Contexte d'isolation du worktree courant, ou None si l'on est dans le clone principal.

    L'offset de port est dérivé du nom de branche : deux worktrees distincts obtiennent
    des ports distincts sans convention à tenir à jour à la main.
    """
    root = Path(capture("git rev-parse --show-toplevel")).resolve()
    common_dir = Path(capture("git rev-parse --git-common-dir"))
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    main_root = common_dir.parent.resolve()

    branch = capture("git rev-parse --abbrev-ref HEAD")
    # Offset déterministe (5..404), pour ne pas retomber sur le port 5000 du clone principal.
    offset = zlib.crc32(branch.encode()) % 400 + 5

    if root == main_root:
        return None

    return {
        "branch": branch,
        "slug": re.sub(r"[^A-Za-z0-9]+", "-", branch).strip("-").lower(),
        "offset": offset,
        "app_port": APP_PORT_BASE + offset,
        "stub_port": STUB_PORT_BASE + offset,
        "root": root,
        "main_root": main_root,
    }


def ports() -> dict:
    """Ports et chemins du checkout courant, worktree ou non."""
    ctx = worktree_context()
    if ctx is None:
        return {
            "app_port": APP_PORT_BASE,
            "stub_port": STUB_PORT_BASE,
            "db": ROOT / "app.db",
            "worktree": None,
        }
    return {
        "app_port": ctx["app_port"],
        "stub_port": ctx["stub_port"],
        "db": ROOT / f"collectives-{ctx['slug']}.db",
        "worktree": ctx,
    }


# ——————————————————————————————————————————————————————————————————————————————
#  Génération des fichiers locaux
# ——————————————————————————————————————————————————————————————————————————————


def upsert_env(path: Path, variables: dict):
    """Insère ou met à jour un bloc balisé dans un fichier .env, sans toucher au reste.

    Ce qui est écrit hors du bloc (réglages personnels, identifiants réels) survit aux
    régénérations.
    """
    block = "\n".join([ENV_BEGIN, *[f"{k}={v}" for k, v in variables.items()], ENV_END])
    existing = path.read_text(encoding="utf-8") if path.is_file() else ENV_HEADER
    pattern = re.compile(
        re.escape(ENV_BEGIN) + ".*?" + re.escape(ENV_END), re.DOTALL
    )

    if pattern.search(existing):
        content = pattern.sub(block, existing)
    else:
        head = existing.rstrip()
        content = (head + "\n\n" if head else "") + block + "\n"

    path.write_text(content, encoding="utf-8")


def write_worktree_files(state: dict):
    """Écrit le fichier local (gitignoré) qui isole le checkout courant."""
    db = state["db"]
    stub_port = state["stub_port"]

    upsert_env(
        ROOT / ".env",
        {
            "COLLECTIVES_PORT": state["app_port"],
            "LOXYA_STUB_PORT": stub_port,
            # Chemin ABSOLU obligatoire : « flask db upgrade » résout les chemins sqlite
            # relatifs depuis le répertoire courant, tandis que Flask-SQLAlchemy les
            # résout depuis instance/ — un chemin relatif crée donc deux bases.
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db}",
            # Sans ceci, l'application interroge le vrai extranet FFCAM au premier login.
            "EXTRANET_DISABLE": 1,
            # Les tâches planifiées ne doivent pas se déclencher seules en développement.
            "SCHEDULER_ENABLED": "false",
            # Pointe vers etc/loxya_stub.py, jamais vers l'API Loxya réelle.
            # Une seule URL : le front et l'API de Loxya partagent le même hôte.
            "LOXYA_URL": f"http://localhost:{stub_port}",
            "LOXYA_API_USERNAME": "dev",
            "LOXYA_API_PASSWORD": "dev",
            "FLASK_DEBUG": 1,
            "SECRET_KEY": "dev-only-not-a-real-secret",
            "ADMINPWD": "foobar2",
        },
    )
    info("Fichier d'isolation généré : .env")


def load_env() -> dict:
    """Lit .env et renvoie les variables, sans dépendre de python-dotenv."""
    path = ROOT / ".env"
    if not path.is_file():
        return {}

    variables = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        variables[key.strip()] = value.strip()
    return variables


def app_env(**overrides) -> dict:
    """Environnement d'exécution de l'application : .env plus FLASK_APP."""
    return {
        **load_env(),
        "FLASK_APP": "collectives:create_app",
        **{k: str(v) for k, v in overrides.items()},
    }


# ——————————————————————————————————————————————————————————————————————————————
#  Amorçage
# ——————————————————————————————————————————————————————————————————————————————


def ensure_venv():
    """Installe les dépendances si le virtualenv du checkout est absent."""
    if not (ROOT / ".venv").is_dir():
        info("Création du virtualenv (uv sync)…")
        run(["uv", "sync"])


def seed_database(state: dict):
    """Amorce la base du worktree par copie de celle du checkout principal.

    Évite de régénérer le jeu de test. Idempotent : ne fait rien si la base existe déjà.
    Les migrations propres à la branche sont appliquées ensuite par ``flask db upgrade``.
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
#  Tâches
# ——————————————————————————————————————————————————————————————————————————————

TASKS = {}


def task(name: str, description: str):
    """Déclare une tâche exposée en ligne de commande."""

    def register(function):
        TASKS[name] = (function, description)
        return function

    return register


@task("info", "Affiche les ports, la base et le contexte du checkout courant")
def task_info(_args):
    """Affiche le contexte d'isolation."""
    state = ports()
    ctx = state["worktree"]

    if ctx is None:
        section("Clone principal")
    else:
        section(f"Worktree isolé : {ctx['branch']} (offset +{ctx['offset']})")

    info(f"Application  : http://localhost:{state['app_port']}")
    info(f"Stub Loxya   : http://localhost:{state['stub_port']}")
    info(f"Base         : {state['db']}"
         + ("" if state["db"].exists() else "  (absente)"))
    return 0


@task("start", "Génère l'isolation, amorce et migre la base, démarre l'application")
def task_start(_args):
    """Démarre l'application, en isolant automatiquement le worktree."""
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


@task("stub", "Démarre le faux serveur Loxya (etc/loxya_stub.py)")
def task_stub(args):
    """Démarre le stub Loxya sur le port du checkout courant."""
    state = ports()
    return run(
        ["uv", "run", "python", "etc/loxya_stub.py", "--port", str(state["stub_port"]),
         *args.rest],
        check=False,
    )


@task("fixtures", "Recharge le jeu de données de test dans la base courante")
def task_fixtures(_args):
    """Régénère le jeu de données de test."""
    run(["uv", "run", "flask", "db", "upgrade"], env=app_env())
    return run(["uv", "run", "python", "etc/test_set.py"], env=app_env(), check=False)


@task("test", "Lance la suite de tests, dans un environnement hermétique")
def task_test(args):
    """Lance pytest sans les variables de développement.

    La suite doit tourner comme en CI : ni la base de développement, ni les variables qui
    neutralisent les services — les tests ont leurs propres mocks dans tests/mock/.
    """
    clean = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("LOXYA_", "SQLALCHEMY_", "EXTRANET_", "SCHEDULER_"))
    }
    return subprocess.run(
        ["uv", "run", "pytest", *args.rest], cwd=ROOT, env=clean, check=False
    ).returncode


@task("lint", "Formate le code et lance le linter, comme la CI")
def task_lint(_args):
    """Formate puis analyse le code."""
    run(["uvx", "ruff", "format"], check=False)
    return run(["uvx", "ruff", "check", "--fix"], check=False)


@task("shell", "Shell Python avec le contexte applicatif")
def task_shell(_args):
    """Ouvre un shell Flask."""
    return run(["uv", "run", "flask", "shell"], env=app_env(), check=False)


@task("destroy", "Supprime la base du checkout courant")
def task_destroy(_args):
    """Supprime la base, après confirmation dans le clone principal."""
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


class _Args:
    """Arguments d'une tâche lancée comme commande console."""

    def __init__(self, rest: list):
        """:param rest: arguments transmis tels quels à la tâche."""
        self.rest = rest


def _entry(name: str):
    """Construit le point d'entrée console d'une tâche.

    Permet ``uv run <tâche>`` en plus de ``./tasks.py <tâche>``.

    :param name: nom de la tâche dans :py:data:`TASKS`
    """

    def entry():
        sys.exit(TASKS[name][0](_Args(sys.argv[1:])) or 0)

    entry.__doc__ = f"Point d'entrée console de la tâche « {name} »."
    return entry


start = _entry("start")
stub = _entry("stub")
fixtures = _entry("fixtures")
lint = _entry("lint")
shell = _entry("shell")
destroy = _entry("destroy")
infos = _entry("info")


def main() -> int:
    """Point d'entrée : analyse les arguments et exécute la tâche demandée."""
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
