"""Module handling Markdown rendering.

Markdown is mainly used in event description.
"""

import re
from html.parser import HTMLParser

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


class _TextExtractor(HTMLParser):
    """Collects the text of an HTML document, turning blocks into line breaks."""

    BLOCK_TAGS = {
        "p", "div", "blockquote", "pre", "table", "ul", "ol", "hr",
        "h1", "h2", "h3", "h4", "h5", "h6",
    }  # fmt: skip
    """Tags separated from the surrounding text by a blank line"""

    LINE_TAGS = {"br", "li", "tr"}
    """Tags starting a new line"""

    def __init__(self):
        """Start with no collected text, outside any ``<pre>`` block."""
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.pre_depth = 0

    def handle_starttag(self, tag, attrs):
        """Open a new line or paragraph before line and block tags."""
        if tag in self.LINE_TAGS:
            self.parts.append("\n")
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n\n")
        if tag == "pre":
            self.pre_depth += 1

    def handle_endtag(self, tag):
        """Close a paragraph after block tags."""
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n\n")
        if tag == "pre":
            self.pre_depth = max(self.pre_depth - 1, 0)

    def handle_data(self, data):
        """Collect the text; outside ``<pre>``, line breaks of the HTML
        source are mere spaces."""
        if not self.pre_depth:
            data = re.sub(r"\s+", " ", data)
        self.parts.append(data)


def html_to_text(html):
    """Convert an HTML text to plain text, keeping only its line breaks.

    Paragraphs and other blocks are separated by a blank line, ``<br>`` become
    line breaks, and every other markup is dropped.

    :param html: HTML text.
    :type html: String
    :return: Plain text.
    :rtype: String
    """
    extractor = _TextExtractor()
    extractor.feed(html or "")
    extractor.close()
    lines = [line.strip() for line in "".join(extractor.parts).split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
