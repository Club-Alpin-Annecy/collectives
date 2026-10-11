"""Long term browser caching of static files.

Static files are served with a version parameter, ``?v=<hash>``, computed from their
content. The URL changes whenever the file changes, so browsers may keep the file
forever instead of checking for a new version on every page.
"""

import hashlib
import os
import re
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
"""Browser cache duration, in seconds, of images and fonts requested without their
current version.

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
without their current version.

:type: set(string)"""

UPLOADS_FOLDER = "uploads/"
"""Folder of the files uploaded while the site runs, relative to the static folder.

Their names may be reused when a file is replaced, so they are never cached without
their version.

:type: string"""

SITE_UPLOADS_FOLDER = "uploads/tech/"
"""Folder of the files uploaded by technicians to configure the site (logo, terms...).

Other uploads are personal (avatars, documents...): they are neither versioned nor
cached, so that a file deleted or replaced, for instance when an account is
anonymized, does not stay in browsers or shared caches.

:type: string"""

MODULE_STATEMENT = re.compile(rb"^(import|export)\s", re.MULTILINE)
"""Pattern identifying JS modules among the scripts.

:type: :py:class:`re.Pattern`"""

STATIC_RESPONSE_CODES = (200, 206, 304)
"""HTTP codes of static responses receiving cache headers. 206 is a partial content,
eg a PDF displayed by the browser.

:type: tuple(int)"""


@lru_cache(maxsize=4096)
def _file_hash(path: str, mtime_ns: int, size: int, inode: int) -> str:  # pylint: disable=unused-argument
    """Hash of a file content.

    File metadata are part of the cache key, so that a modified file gets a new hash
    without restarting the application.

    :param path: Absolute path of the file
    :param mtime_ns: Modification time of the file
    :param size: Size of the file
    :param inode: Inode of the file, which changes when a file is replaced
    :return: A short hash of the file content
    """
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()[:12]


def _is_personal_upload(filename: str) -> bool:
    """Whether a static file has been uploaded by a user.

    :param filename: Path of the file, relative to the static folder
    """
    return filename.startswith(UPLOADS_FOLDER) and not filename.startswith(
        SITE_UPLOADS_FOLDER
    )


def static_file_version(filename: str) -> str | None:
    """Version of a static file, derived from its content.

    :param filename: Path of the file, relative to the static folder
    :return: The version, or None if the file does not exist or is a personal upload
    """
    if _is_personal_upload(filename):
        return None
    path = safe_join(current_app.static_folder, filename)
    if path is None:
        return None
    try:
        stat = os.stat(path)
        return _file_hash(path, stat.st_mtime_ns, stat.st_size, stat.st_ino)
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

    A version that does not match the current file is not kept forever: it may come
    from a page rendered before a deployment, or by another server still running the
    previous release. Images and fonts requested without their current version are
    cached for :py:data:`UNVERSIONED_MAX_AGE`, unless they have been uploaded while
    the site runs.
    """
    if (
        request.endpoint != "static"
        or response.status_code not in STATIC_RESPONSE_CODES
    ):
        return response
    filename = (request.view_args or {}).get("filename", "")
    version = request.args.get(VERSION_PARAMETER)
    if version and version == static_file_version(filename):
        response.cache_control.public = True
        response.cache_control.max_age = VERSIONED_MAX_AGE
        response.cache_control.immutable = True
        response.cache_control.no_cache = None
    elif (
        not filename.startswith(UPLOADS_FOLDER)
        and Path(filename).suffix.lower() in UNVERSIONED_CACHED_SUFFIXES
    ):
        response.cache_control.public = True
        response.cache_control.max_age = UNVERSIONED_MAX_AGE
        response.cache_control.no_cache = None
    return response


def _module_imports(folder: str) -> dict[str, str]:
    """Versioned URLs of the JS modules of a folder.

    :param folder: Folder of the modules, relative to the static folder
    :return: Dictionary from the unversioned URL to the versioned one
    """
    root = Path(current_app.static_folder)
    imports = {}
    for path in sorted((root / folder).rglob("*.js")):
        if not MODULE_STATEMENT.search(path.read_bytes()):
            # Classic script, never imported
            continue
        versioned = url_for("static", filename=path.relative_to(root).as_posix())
        imports[versioned.split("?", 1)[0]] = versioned
    return imports


def static_importmap(imports: dict[str, str], folder: str = "js") -> dict:
    """Import map of a page, pointing local JS modules to their versioned URL.

    Modules import each other with relative paths, which do not carry the version.
    The import map redirects such imports to the versioned URL of the module. It is
    computed once, unless in debug mode where files change while the site runs.

    :param imports: Other entries of the import map, eg libraries from a CDN
    :param folder: Folder of the modules, relative to the static folder
    :return: The import map, to be serialized as JSON
    """
    cache = current_app.extensions.setdefault("static_importmap", {})
    if current_app.debug or folder not in cache:
        cache[folder] = _module_imports(folder)
    return {"imports": {**imports, **cache[folder]}}


def init_app(app: Flask):
    """Registers the hooks versioning static files.

    :param app: The Flask application
    """
    app.url_defaults(_add_static_version)
    app.after_request(_cache_versioned_static)
