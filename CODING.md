
# Python Coding Style
 * Always format Python code using [black](https://github.com/psf/black) 
 * Follow the guidelines from https://google.github.io/styleguide/pyguide.html
   (except for Section 3, "Python Style rules" -- there `black` should prevail)
 * Code should be validated with `pylint` and the included `pylintrc`. 
 * Documentation shall be updated for every commit which modify a class or method parameters.

# HTML
 * indent with space

# All language type:
 * Do not add blank spaces at end of line
 * Never align with tabs, always using spaces

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
