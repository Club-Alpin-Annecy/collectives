""" List of crawler. Data comes from https://github.com/monperrus/crawler-user-agents"""

from functools import wraps
import json, os, re

from flask import request, redirect, url_for
from flask_login import current_user

CRAWLERS = None


def get_crawlers():
    """Get the crawler list.

    Will try to get it from the cache. If not, it will load the cache
    from data/crawler-user-agents.json

    :returns: the list of known crawlers"""
    global CRAWLERS
    if not CRAWLERS:
        path = os.path.dirname(__file__) + "/../data/crawler-user-agents.json"
        with open(path) as f:
            CRAWLERS = json.load(f)

    return CRAWLERS


def is_crawler():
    """Check if current agent is a crawler.

    :returns: True if request user agent match a crawler pattern."""

    agent = request.headers.get("User-Agent")

    for crawler in get_crawlers():
        if re.search(crawler["pattern"], agent):
            return True
    return False


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
        def innerF(*args, **kwargs):
            """Fonction to decide if an unauthenticated crawler tries to access"""
            if current_user:
                if current_user.is_authenticated:
                    return func(*args, **kwargs)
            if is_crawler():
                return redirect(url_for(url, **kwargs))
            return func(*args, **kwargs)

        return innerF

    return crawlers_catcher_base
