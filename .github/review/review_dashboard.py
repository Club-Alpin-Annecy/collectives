"""Dashboard of the open pull requests.

Takes one snapshot of the open PRs through `gh api graphql`, groups them by
what is needed from whom, and renders the same list twice: a static HTML page
for GitHub Pages and the body of one pinned issue. No model is involved.
"""

import argparse
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_bot  # pylint: disable=wrong-import-position

GROUPS = (
    ("needed", "Où on a besoin de vous"),
    ("release", "Bloque la release"),
    ("open_questions", "Questions ouvertes sans réponse"),
    ("to_review", "À relire — personne n'est désigné"),
    ("waiting_author", "En attente de l'auteur"),
    ("outside_no_reply", "Contributeurs extérieurs sans réponse après 7 jours"),
    ("deps_ready", "Dépendances prêtes"),
    ("approved_not_merged", "Approuvées non fusionnées"),
)
APPROVED = "APPROVED"
CHANGES_REQUESTED = "CHANGES_REQUESTED"
ISSUE_MARKER = "<!-- collectives-dashboard -->"
ISSUE_TITLE = "Tableau de revue des pull requests"
OUTSIDE_DAYS = 7
VERY_OLD_DAYS = 365
DECIDING_STATES = (APPROVED, CHANGES_REQUESTED)
DEFAULT_MAINTAINERS = "jnguiot,gdaviet"

RELEASE_LABELS = ("prioritaire",)
RELEASE_LABEL_PATTERN = re.compile(r"^v\d+(\.\d+)*$")
CHECKS_SUCCESS = "SUCCESS"
READY_BUMPS = ("patch", "minor")
DEPENDABOT_LOGINS = ("dependabot", "app/dependabot", "dependabot[bot]")
BUMP_PATTERN = re.compile(r"[Bb]ump .+ from (\S+) to (\S+)")
BUMP_GROUP_PATTERN = re.compile(r"[Bb]ump the (patch|minor|major)\b")
VERDICT_PATTERN = re.compile(r"^Verdict: (.+)$", re.MULTILINE)
BOT_LOGINS = ("github-actions", review_bot.BOT_LOGIN)
MONTHS = (
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)
MAX_PRS = 100

SNAPSHOT_QUERY = (
    """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: %d, orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes {
        number title url isDraft createdAt reviewDecision
        author { login }
        labels(first: 30) { nodes { name } }
        reviews(last: 50) { nodes { state submittedAt author { login } } }
        reviewThreads(first: 50) {
          nodes {
            isResolved
            comments(last: 1) { nodes { createdAt author { login } } }
          }
        }
        commits(last: 1) { nodes { commit { statusCheckRollup { state } } } }
        reviewRequests(first: 20) {
          nodes { requestedReviewer { ... on User { login } } }
        }
        comments(first: 100) { nodes { body author { login } } }
      }
    }
  }
}
"""
    % MAX_PRS
)

PIN_MUTATION = """
mutation($id: ID!) { pinIssue(input: {issueId: $id}) { issue { number } } }
"""

PAGE_STYLE = """\
:root{--bg:#fff;--fg:#1c1e21;--muted:#5f6670;--line:#d8dce1;--card:#f5f6f8;--link:#0b5cad}
@media (prefers-color-scheme:dark){:root{--bg:#15171a;--fg:#e6e8eb;--muted:#9aa1ab;--line:#2d3138;--card:#1e2126;--link:#6cb2ff}}
*{box-sizing:border-box}
body{margin:0 auto;max-width:56rem;padding:1rem 16px 3rem;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
a{color:var(--link)}
h1{font-size:1.5rem;margin:.5rem 0}
h2{font-size:1.15rem;margin:1.75rem 0 .5rem;border-bottom:1px solid var(--line);padding-bottom:.25rem}
h3{font-size:1rem;margin:1rem 0 .25rem}
.meta{color:var(--muted);font-size:.9rem}
.filters{display:flex;flex-wrap:wrap;gap:.75rem;margin:1rem 0}
.filters label{display:flex;flex-direction:column;gap:.2rem;min-width:0;max-width:100%}
select{max-width:100%;font:inherit;padding:.3rem;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px}
ul{list-style:none;margin:0;padding:0}
li{background:var(--card);border:1px solid var(--line);border-radius:6px;margin:.4rem 0;padding:.5rem .75rem;overflow-wrap:anywhere}
.detail{color:var(--muted);font-size:.9rem}
[hidden]{display:none}
"""

PAGE_SCRIPT = """\
const person = document.getElementById('person');
const group = document.getElementById('group');
function apply() {
  document.querySelectorAll('li[data-pr]').forEach(li => {
    const okPerson = !person.value || li.dataset.people.split(' ').includes(person.value);
    const okGroup = !group.value || li.dataset.group === group.value;
    li.hidden = !(okPerson && okGroup);
  });
  document.querySelectorAll('section, .block').forEach(el => {
    el.hidden = !el.querySelector('li[data-pr]:not([hidden])');
  });
}
person.addEventListener('change', apply);
group.addEventListener('change', apply);
apply();
"""


def parse_time(value: str) -> datetime:
    """Parses an ISO 8601 date, with a `Z` or an offset, into an aware datetime.

    Args:
        value: The ISO date text.

    Returns:
        The datetime, in UTC.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def short_date(value: str) -> str:
    """Formats an ISO date as a short French date, e.g. `29 oct.`.

    Args:
        value: The ISO date text.

    Returns:
        The short date, or `value` unchanged when it is not a date.
    """
    try:
        moment = parse_time(value)
    except ValueError:
        return value
    return f"{moment.day} {MONTHS[moment.month - 1]}"


def is_release_blocker(pr: dict) -> bool:
    """Tells whether a PR carries a release label.

    Args:
        pr: The snapshot PR.

    Returns:
        True for `prioritaire` or a version label such as `v39.0`.
    """
    return any(
        label in RELEASE_LABELS or RELEASE_LABEL_PATTERN.match(label)
        for label in pr["labels"]
    )


def last_verdicts(pr: dict) -> dict[str, dict]:
    """Keeps each reviewer's last approving or blocking review.

    Args:
        pr: The snapshot PR.

    Returns:
        Reviewer login to review, without the author's own reviews. A later
        comment does not replace an earlier verdict.
    """
    verdicts: dict[str, dict] = {}
    for item in pr["reviews"]:
        if item["author"] != pr["author"] and item["state"] in DECIDING_STATES:
            verdicts[item["author"]] = item
    return verdicts


def decision(pr: dict) -> str | None:
    """Gives the review decision, derived from the reviews when GitHub has none.

    Args:
        pr: The snapshot PR.

    Returns:
        `APPROVED`, `CHANGES_REQUESTED` or None.
    """
    if pr["review_decision"] is not None:
        return pr["review_decision"]
    states = {item["state"] for item in last_verdicts(pr).values()}
    for state in (CHANGES_REQUESTED, APPROVED):
        if state in states:
            return state
    return None


def deciders(pr: dict, state: str) -> list[str]:
    """Lists the reviewers whose last verdict is `state`."""
    return [name for name, item in last_verdicts(pr).items() if item["state"] == state]


def age_text(created_at: datetime, now: datetime) -> str:
    """Says in French when a PR was opened and how old it is.

    Args:
        created_at: The creation time.
        now: The current time.

    Returns:
        E.g. `ouverte le 7 oct. (22 j)`; the year appears when it is not this year.
    """
    year = f" {created_at.year}" if created_at.year != now.year else ""
    return (
        f"ouverte le {created_at.day} {MONTHS[created_at.month - 1]}{year} "
        f"({(now - created_at).days} j)"
    )


def needed_by(pr: dict, maintainers: list[str]) -> list[str]:
    """Lists the maintainers who are needed on a PR.

    Args:
        pr: The snapshot PR.
        maintainers: The maintainers' logins, in display order.

    Returns:
        The needed maintainers, in the order of `maintainers`.
    """
    if pr["is_draft"] or decision(pr) is not None:
        return []
    requested = [name for name in maintainers if name in pr["requested_reviewers"]]
    if requested:
        return requested
    if pr["is_dependabot"] and pr["bump_type"] == "major":
        return list(maintainers)
    return []


def classify(pr: dict, maintainers: list[str], now: datetime) -> set[str]:
    """Finds the groups a PR belongs to.

    Args:
        pr: The snapshot PR.
        maintainers: The maintainers' logins.
        now: The current time.

    Returns:
        The group keys; empty for a draft.
    """
    if pr["is_draft"]:
        return set()
    found = set()
    if needed_by(pr, maintainers):
        found.add("needed")
    if is_release_blocker(pr):
        found.add("release")
    if any(
        thread["last_author"] != pr["author"] for thread in pr["unresolved_threads"]
    ):
        found.add("open_questions")
    if decision(pr) == CHANGES_REQUESTED:
        found.add("waiting_author")
    age = now - parse_time(pr["created_at"])
    outside = (
        pr["author"] not in maintainers
        and not pr["is_dependabot"]
        and not pr["reviews"]
        and not pr["maintainer_commented"]
        and age.days > OUTSIDE_DAYS
    )
    if outside:
        found.add("outside_no_reply")
    if (
        not outside
        and not pr["is_dependabot"]
        and decision(pr) is None
        and not needed_by(pr, maintainers)
    ):
        found.add("to_review")
    if (
        pr["is_dependabot"]
        and pr["bump_type"] in READY_BUMPS
        and pr["checks_state"] == CHECKS_SUCCESS
    ):
        found.add("deps_ready")
    if decision(pr) == APPROVED:
        found.add("approved_not_merged")
    return found


def build_groups(prs: list[dict], maintainers: list[str], now: datetime) -> dict:
    """Sorts the PRs into the dashboard groups.

    Args:
        prs: The snapshot PRs.
        maintainers: The maintainers' logins.
        now: The current time.

    Returns:
        A dict with every group key, PRs sorted by number. `needed` maps each
        maintainer to the list of PRs that need them.
    """
    groups: dict = {key: [] for key, _ in GROUPS}
    groups["needed"] = {name: [] for name in maintainers}
    for pr in sorted(prs, key=lambda item: item["number"]):
        for key in classify(pr, maintainers, now):
            if key == "needed":
                for name in needed_by(pr, maintainers):
                    groups["needed"][name].append(pr)
            else:
                groups[key].append(pr)
    return groups


def detail(key: str, pr: dict, now: datetime) -> str:
    """Describes, in French, why a PR is in a group.

    Args:
        key: The group key.
        pr: The snapshot PR.
        now: The current time.

    Returns:
        A short text, with the bot's verdict appended when known.
    """
    created = parse_time(pr["created_at"])
    age = (now - created).days
    if key == "needed":
        if pr["is_dependabot"]:
            text = "montée de version majeure, à décider"
        else:
            text = "relecture demandée à " + ", ".join(pr["requested_reviewers"])
    elif key == "release":
        text = "étiquettes : " + ", ".join(
            label
            for label in pr["labels"]
            if label in RELEASE_LABELS or RELEASE_LABEL_PATTERN.match(label)
        )
    elif key == "open_questions":
        last = [
            thread
            for thread in pr["unresolved_threads"]
            if thread["last_author"] != pr["author"]
        ][-1]
        text = (
            f"remarque de {last['last_author']} sans réponse "
            f"depuis le {short_date(last['created_at'])}"
        )
    elif key == "to_review":
        text = "très ancienne : relancer ou fermer ?" if age > VERY_OLD_DAYS else ""
    elif key == "waiting_author":
        blocking = last_verdicts(pr)
        names = deciders(pr, CHANGES_REQUESTED)
        text = "changements demandés"
        if names:
            text += f" par {names[0]}"
            when = blocking[names[0]].get("submitted_at")
            if when:
                text += f" le {short_date(when)}"
    elif key == "outside_no_reply":
        text = "aucune réponse du club"
    elif key == "deps_ready":
        text = f"CI verte, mise à jour {pr['bump_type']}"
    else:
        names = deciders(pr, APPROVED)
        text = "approuvée" + (f" par {', '.join(names)}" if names else "")
        text += ", non fusionnée"
    text = " · ".join(part for part in (text, age_text(created, now)) if part)
    if pr.get("verdict"):
        text += f" ; verdict du bot : {pr['verdict']}"
    return text


def render_issue(groups: dict, dashboard_url: str, now: datetime) -> str:
    """Renders the body of the pinned issue.

    Args:
        groups: The result of `build_groups`.
        dashboard_url: The address of the dashboard page.
        now: The current time.

    Returns:
        The Markdown body, starting with `ISSUE_MARKER`.
    """
    lines = [
        ISSUE_MARKER,
        f"Mis à jour le {short_date(now.isoformat())} ({now:%H:%M} UTC). "
        f"Version filtrable : {dashboard_url}",
    ]

    def pr_line(key: str, pr: dict) -> str:
        return (
            f"- [#{pr['number']}]({pr['url']}) {pr['title']} ({pr['author']}) — "
            f"{detail(key, pr, now)}"
        )

    for key, title in GROUPS:
        content = groups[key]
        if not (any(content.values()) if key == "needed" else content):
            continue
        lines += ["", f"## {title}"]
        if key == "needed":
            for person, prs in content.items():
                if prs:
                    lines += ["", f"### {person}", *(pr_line(key, pr) for pr in prs)]
        else:
            lines += ["", *(pr_line(key, pr) for pr in content)]
    return "\n".join(lines) + "\n"


def render_html(groups: dict, issue_url: str, now: datetime) -> str:
    """Renders the dashboard as one self-contained HTML page.

    Args:
        groups: The result of `build_groups`.
        issue_url: The address of the pinned issue.
        now: The current time.

    Returns:
        The HTML document.
    """
    escape = html.escape
    people_by_pr: dict[int, list[str]] = {}
    for person, prs in groups["needed"].items():
        for pr in prs:
            people_by_pr.setdefault(pr["number"], []).append(person)

    def pr_item(key: str, pr: dict) -> str:
        people = escape(" ".join(people_by_pr.get(pr["number"], [])), quote=True)
        return (
            f'<li data-group="{key}" data-pr="{pr["number"]}" data-people="{people}">'
            f'<a href="{escape(pr["url"], quote=True)}">#{pr["number"]}</a> '
            f"{escape(pr['title'])} ({escape(pr['author'])})<br>"
            f'<span class="detail">{escape(detail(key, pr, now))}</span></li>'
        )

    sections = []
    for key, title in GROUPS:
        content = groups[key]
        if key == "needed":
            body = "".join(
                f'<div class="block"><h3>{escape(person)}</h3><ul>'
                + "".join(pr_item(key, pr) for pr in prs)
                + "</ul></div>"
                for person, prs in content.items()
                if prs
            )
        else:
            body = (
                "<ul>" + "".join(pr_item(key, pr) for pr in content) + "</ul>"
                if content
                else ""
            )
        if body:
            sections.append(f"<section><h2>{escape(title)}</h2>{body}</section>")

    person_options = "".join(
        f'<option value="{escape(name, quote=True)}">{escape(name)}</option>'
        for name in groups["needed"]
    )
    group_options = "".join(
        f'<option value="{key}">{escape(title)}</option>' for key, title in GROUPS
    )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revue des pull requests</title>
<style>
{PAGE_STYLE}</style>
</head>
<body>
<h1>Revue des pull requests</h1>
<p class="meta">Généré le {short_date(now.isoformat())} à {now:%H:%M} UTC.
Même liste dans <a href="{escape(issue_url, quote=True)}">l'issue épinglée</a>.</p>
<div class="filters">
<label>Personne <select id="person"><option value="">Tous</option>{person_options}</select></label>
<label>Groupe <select id="group"><option value="">Tous</option>{group_options}</select></label>
</div>
{"".join(sections)}
<script>
{PAGE_SCRIPT}</script>
</body>
</html>
"""


def gh_api(args: list[str], stdin: str | None = None) -> str:
    """Runs `gh api` and returns its output.

    Args:
        args: Arguments after `gh api`.
        stdin: Text sent on the standard input, if any.

    Returns:
        The standard output.

    Raises:
        RuntimeError: When the command fails.
    """
    result = subprocess.run(
        ["gh", "api", *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip().splitlines()[-1:] or ["unknown error"]
        raise RuntimeError(f"gh api {args[-1]} failed: {message[0]}")
    return result.stdout


def bump_type(title: str) -> str | None:
    """Reads the kind of version bump from a Dependabot title.

    Args:
        title: The PR title.

    Returns:
        `patch`, `minor`, `major`, or None when the title does not say.
    """
    grouped = BUMP_GROUP_PATTERN.match(title)
    if grouped:
        return grouped.group(1)
    match = BUMP_PATTERN.match(title)
    if not match:
        return None
    old, new = (re.findall(r"\d+", version) for version in match.groups())
    for index, kind in enumerate(("major", "minor", "patch")):
        old_part = old[index] if index < len(old) else "0"
        new_part = new[index] if index < len(new) else "0"
        if old_part != new_part:
            return kind
    return None


def login(node: dict | None) -> str:
    """Returns the login of a GraphQL actor, empty when the account is gone."""
    return (node or {}).get("login") or ""


def to_snapshot(node: dict, maintainers: list[str]) -> dict:
    """Maps one GraphQL pull request node to a snapshot PR.

    Args:
        node: The GraphQL node.
        maintainers: The maintainers' logins.

    Returns:
        The snapshot PR, with a `verdict` key when our review comment has one.
    """
    author = login(node["author"])
    comments = node["comments"]["nodes"]
    verdict = None
    for comment in comments:
        if login(comment["author"]) in BOT_LOGINS and comment["body"].startswith(
            review_bot.MARKER
        ):
            found = VERDICT_PATTERN.search(comment["body"])
            verdict = found.group(1) if found else None
    commits = node["commits"]["nodes"]
    rollup = commits[0]["commit"]["statusCheckRollup"] if commits else None
    threads = []
    for thread in node["reviewThreads"]["nodes"]:
        last = thread["comments"]["nodes"]
        if not thread["isResolved"] and last:
            threads.append(
                {
                    "last_author": login(last[0]["author"]),
                    "created_at": last[0]["createdAt"],
                }
            )
    is_dependabot = author in DEPENDABOT_LOGINS
    return {
        "number": node["number"],
        "title": node["title"],
        "url": node["url"],
        "author": author,
        "is_draft": node["isDraft"],
        "created_at": node["createdAt"],
        "labels": [label["name"] for label in node["labels"]["nodes"]],
        "review_decision": node["reviewDecision"],
        "reviews": [
            {
                "author": login(review["author"]),
                "state": review["state"],
                "submitted_at": review["submittedAt"],
            }
            for review in node["reviews"]["nodes"]
        ],
        "maintainer_commented": any(
            login(comment["author"]) in maintainers for comment in comments
        ),
        "unresolved_threads": threads,
        "checks_state": rollup["state"] if rollup else None,
        "is_dependabot": is_dependabot,
        "bump_type": bump_type(node["title"]) if is_dependabot else None,
        "requested_reviewers": [
            login(request["requestedReviewer"])
            for request in node["reviewRequests"]["nodes"]
            if request["requestedReviewer"]
        ],
        "verdict": verdict,
    }


def load_snapshot(repo: str, maintainers: list[str]) -> list[dict]:
    """Reads the open pull requests of a repository.

    Args:
        repo: The repository, as `owner/name`.
        maintainers: The maintainers' logins.

    Returns:
        The snapshot PRs.
    """
    owner, name = repo.split("/", 1)
    output = gh_api(
        [
            "graphql",
            "-f",
            f"query={SNAPSHOT_QUERY}",
            "-f",
            f"owner={owner}",
            "-f",
            f"name={name}",
        ]
    )
    nodes = json.loads(output)["data"]["repository"]["pullRequests"]["nodes"]
    return [to_snapshot(node, maintainers) for node in nodes]


def find_issue(repo: str) -> dict | None:
    """Finds the dashboard issue among the open issues.

    Args:
        repo: The repository, as `owner/name`.

    Returns:
        The issue dict, or None when there is none.
    """
    issues = json.loads(gh_api([f"repos/{repo}/issues?state=open&per_page=100"]))
    for issue in issues:
        if (
            "pull_request" not in issue
            and issue["user"]["login"] == review_bot.BOT_LOGIN
            and (issue["body"] or "").startswith(ISSUE_MARKER)
        ):
            return issue
    return None


def create_issue(repo: str) -> dict:
    """Creates the dashboard issue with a placeholder body and tries to pin it.

    Args:
        repo: The repository, as `owner/name`.

    Returns:
        The created issue dict.
    """
    payload = json.dumps({"title": ISSUE_TITLE, "body": ISSUE_MARKER})
    issue = json.loads(gh_api([f"repos/{repo}/issues", "--input", "-"], stdin=payload))
    try:
        gh_api(
            ["graphql", "-f", f"query={PIN_MUTATION}", "-f", f"id={issue['node_id']}"]
        )
    except RuntimeError as error:
        print(f"could not pin the issue: {error}", file=sys.stderr)
    return issue


def monday_comment(groups: dict, now: datetime) -> str:
    """Writes the short weekly comment.

    Args:
        groups: The result of `build_groups`.
        now: The current time.

    Returns:
        The comment text: the date and the count per group.
    """
    counts = []
    for key, title in GROUPS:
        content = groups[key]
        total = (
            len({pr["number"] for prs in content.values() for pr in prs})
            if (key == "needed")
            else len(content)
        )
        if total:
            counts.append(f"{title} : {total}")
    summary = " ; ".join(counts) or "rien à signaler"
    return f"Point du lundi {short_date(now.isoformat())} — {summary}."


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parses the command line.

    Args:
        argv: The arguments, without the program name.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--out", required=True, type=Path, help="output directory")
    parser.add_argument("--dry-run", action="store_true", help="never touch GitHub")
    parser.add_argument("--monday", action="store_true", help="post the weekly comment")
    parser.add_argument("--maintainers", default=DEFAULT_MAINTAINERS)
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> None:
    """Builds the dashboard and, unless in dry run, updates the issue.

    Args:
        args: The parsed arguments.
    """
    now = datetime.now(timezone.utc)
    maintainers = [name.strip() for name in args.maintainers.split(",") if name.strip()]
    owner, name = args.repo.split("/", 1)
    dashboard_url = f"https://{owner.lower()}.github.io/{name}/"
    groups = build_groups(load_snapshot(args.repo, maintainers), maintainers, now)

    issue = None
    if not args.dry_run:
        issue = find_issue(args.repo) or create_issue(args.repo)
    issue_url = issue["html_url"] if issue else f"https://github.com/{args.repo}/issues"
    body = render_issue(groups, dashboard_url, now)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "index.html").write_text(
        render_html(groups, issue_url, now), encoding="utf-8"
    )
    if args.dry_run:
        (args.out / "issue.md").write_text(body, encoding="utf-8")
        return
    gh_api(
        [f"repos/{args.repo}/issues/{issue['number']}", "-X", "PATCH", "--input", "-"],
        stdin=json.dumps({"body": body}),
    )
    if args.monday:
        gh_api(
            [f"repos/{args.repo}/issues/{issue['number']}/comments", "--input", "-"],
            stdin=json.dumps({"body": monday_comment(groups, now)}),
        )


def main(argv: list[str]) -> int:
    """Runs the dashboard.

    Args:
        argv: The arguments, without the program name.

    Returns:
        The exit code: 0 on success, 1 on error.
    """
    args = parse_args(argv)
    try:
        run(args)
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
