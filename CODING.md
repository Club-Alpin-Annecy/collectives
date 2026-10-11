
# Python Coding Style
 * Always format Python code using [ruff](https://astral.sh/ruff) 
 * Follow the guidelines from https://google.github.io/styleguide/pyguide.html, except:
 ** for Section 3, "Python Style rules" -- there `ruff` should prevail
 ** import (see 2.2), where import of functions and classes are authorized.
 * Code should be validated with `ruff check` as configured in `pyproject.toml`. 
 * Documentation shall be updated for every commit which modify a class or method parameters.

# HTML
 * indent with space

# All language type:
 * Do not add blank spaces at end of line
 * Never align with tabs, always using spaces

# Configuration
 * Store new settings preferably in `collectives/configuration.yaml` (hot configuration): it is stored in database, edited live by technicians in `/technician/configuration`, and read through `Configuration.SETTING_NAME`.
 * This includes the credentials of third-party services, like `EXTRANET_ACCOUNT_PWD` or `SMTP_PASSWORD`: mark secrets with `hidden: true`, so they are never displayed.
 * Give the items of an optional feature `requires: <SETTING>`: they are then only shown and editable when that `config.py` setting is true. The code is shared between clubs that do not all use every feature.
 * Keep `config.py` (cold configuration, requires a restart) for what cannot live in database: highly technical settings, the database access, and the switch of an optional feature.
 * Never define in `config.py` a setting that lives in `configuration.yaml`: the file would take precedence over the database. Read hot settings with `Configuration.SETTING_NAME`, not `app.config.get(...)`, which never looks into the database.

# Commit :
 * message in English
 
# Github merge: 
(for project maintainers)
 * Add a tag in merge commit message (eg. [FEATURE] xxxxxxx )
   * `[FEATURE]` : contains a new feature.
   * `[FIX]` : fix a bug 
   * `[INTERNAL]` : no functional changes (refactoring, documentation, test, performance, etc...)
   * `[OTHER]`
   * Don't include if it should not be in release note.
 * If the PR is linked to an issue, use [github link in commit](https://help.github.com/en/github/managing-your-work-on-github/linking-a-pull-request-to-an-issue#linking-a-pull-request-to-an-issue-using-a-keyword) just after the tag. in merge commit, eg:
   * `[FIX] Fixes #123 : event list title fixed`
   * `[FEATURE] Closes #124 : add info on event`

Note: to generate release note:
``` for tag in FEATURE FIX INTERNAL OTHER ; do echo $tag:;  git log --pretty="%s" --grep="\[$tag\]" v0.5..v0.6  ; echo; done ```
