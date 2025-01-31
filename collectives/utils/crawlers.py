"""List of crawler. Data comes from https://github.com/monperrus/crawler-user-agents"""

from functools import wraps, cache
import json
import os
import re

from flask import request, redirect, url_for
from flask_login import current_user


@cache
def get_crawlers_pattern() -> re.Pattern:
    """:returns: a global pattern matching any crawler"""

    path = os.path.dirname(__file__) + "/../data/crawler-user-agents.json"
    with open(path, encoding="utf-8") as file:
        crawlers = json.load(file)

    global_pattern = "|".join(crawler["pattern"] for crawler in crawlers)
    return re.compile(global_pattern)


def is_crawler():
    """Check if current agent is a crawler.

    :returns: True if request user agent match a crawler pattern."""

    agent = request.headers.get("User-Agent")
    return agent and re.search(get_crawlers_pattern(), agent)


def crawlers_catcher(url):
    """Function to create a specific decorator which will redirect unauthenticated crawlers
    to the designated url.

    Decorated function and redirected function MUST have the arguments.

    How to use:
    .. code-block:: python

        @crawlers_catcher('event.preview')
        @blueprint.route("/", methods=["GET", "POST"])
        def event():
            return "for users"

        def preview():
            return "for crawler"

    :param string url: the function to be called using url_for syntax. ie blueprint.function
    :returns: the right decorator for the function"""

    @wraps(url)
    def crawlers_catcher_base(func):
        """Decorator to reroute unauthenticated crawlers to preview page.

        :param func: Function to protect"""

        @wraps(func)
        def inner_function(*args, **kwargs):
            """Fonction to decide if an unauthenticated crawler tries to access"""
            if current_user:
                if current_user.is_authenticated:
                    return func(*args, **kwargs)
            if is_crawler():
                return redirect(url_for(url, **kwargs))
            return func(*args, **kwargs)

        return inner_function

    return crawlers_catcher_base
