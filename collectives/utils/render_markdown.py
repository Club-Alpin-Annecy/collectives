""" Module handling Markdown rendering.

Markdown is mainly used in event description.
"""
import cmarkgfm
from cmarkgfm.cmark import Options as cmarkgfmOptions
from markupsafe import Markup


def markdown_to_html(text):
    """Convert a markdown text to HTML, unless is already marked as markup-safe.

    :param text: Markdown text.
    :type text: String
    :return: Converted HTML text.
    :rtype: String

    """
    if isinstance(text, Markup):
        return text

    return cmarkgfm.github_flavored_markdown_to_html(
        text,
        options=cmarkgfmOptions.CMARK_OPT_SMART | cmarkgfmOptions.CMARK_OPT_HARDBREAKS,
    )
