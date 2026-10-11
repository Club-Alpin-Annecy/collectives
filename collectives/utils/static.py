"""Long term browser caching of static files.

Static files are served with a version parameter, ``?v=<hash>``, computed from their
content. The URL changes whenever the file changes, so browsers may keep the file
forever instead of checking for a new version on every page.
"""

import hashlib
import os
from functools import lru_cache
from pathlib import Path

from flask import Flask, Response, current_app, request, url_for
from werkzeug.security import safe_join

VERSION_PARAMETER = "v"
"""Name of the URL parameter holding the version of a static file.

:type: string"""

VERSIONED_MAX_AGE = 365 * 24 * 3600
"""Browser cache duration, in seconds, of a static file requested with its version.

:type: int"""

UNVERSIONED_MAX_AGE = 3600
"""Browser cache duration, in seconds, of images and fonts requested without version.

Some of them have their path written in JS or CSS files, so they cannot be versioned.
They only change on deployments: a short delay is acceptable. Scripts and styles
requested without version are always checked, so that a page never mixes two
releases.

:type: int"""

UNVERSIONED_CACHED_SUFFIXES = {
    ".eot",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
}
"""Suffixes of the files cached for :py:data:`UNVERSIONED_MAX_AGE` when requested
without version.

:type: set(string)"""


@lru_cache(maxsize=4096)
def _file_hash(path: str, mtime_ns: int) -> str:  # pylint: disable=unused-argument
    """Hash of a file content. The modification time is part of the cache key, so
    that a modified file gets a new hash without restarting the application.

    :param path: Absolute path of the file
    :param mtime_ns: Modification time of the file
    :return: A short hash of the file content
    """
    with open(path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()[:12]


def static_file_version(filename: str) -> str | None:
    """Version of a static file, derived from its content.

    :param filename: Path of the file, relative to the static folder
    :return: The version, or None if the file does not exist
    """
    path = safe_join(current_app.static_folder, filename)
    if path is None:
        return None
    try:
        mtime_ns = os.stat(path).st_mtime_ns
        return _file_hash(path, mtime_ns)
    except OSError:
        return None


def _add_static_version(endpoint: str, values: dict):
    """URL defaults hook adding the version to URLs of static files."""
    if endpoint != "static" or VERSION_PARAMETER in values:
        return
    version = static_file_version(values.get("filename", ""))
    if version is not None:
        values[VERSION_PARAMETER] = version


def _cache_versioned_static(response: Response) -> Response:
    """Lets browsers keep a static file forever when it is requested with its
    current version.

    A version that does not match the current file is not cached: it may come from
    a page rendered before a deployment, or by another server still running the
    previous release. Images and fonts without version are cached for
    :py:data:`UNVERSIONED_MAX_AGE`.
    """
    if request.endpoint != "static" or response.status_code not in (200, 304):
        return response
    version = request.args.get(VERSION_PARAMETER)
    filename = (request.view_args or {}).get("filename", "")
    if version:
        if version == static_file_version(filename):
            response.cache_control.public = True
            response.cache_control.max_age = VERSIONED_MAX_AGE
            response.cache_control.immutable = True
            response.cache_control.no_cache = None
    elif Path(filename).suffix.lower() in UNVERSIONED_CACHED_SUFFIXES:
        response.cache_control.public = True
        response.cache_control.max_age = UNVERSIONED_MAX_AGE
        response.cache_control.no_cache = None
    return response


def static_importmap(folder: str = "js") -> dict[str, str]:
    """Import map entries pointing JS modules to their versioned URL.

    Modules import each other with relative paths, which do not carry the version.
    Declared in the page import map, these entries redirect such imports to the
    versioned URL of the module.

    :param folder: Folder of the modules, relative to the static folder
    :return: Dictionary from the unversioned URL to the versioned one
    """
    root = Path(current_app.static_folder)
    imports = {}
    for path in sorted((root / folder).rglob("*.js")):
        filename = path.relative_to(root).as_posix()
        versioned = url_for("static", filename=filename)
        imports[versioned.split("?", 1)[0]] = versioned
    return imports


def init_app(app: Flask):
    """Registers the hooks versioning static files.

    :param app: The Flask application
    """
    app.url_defaults(_add_static_version)
    app.after_request(_cache_versioned_static)
