import re
import markdown
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension

# pylint: disable=C0301
URI_REGEX = re.compile(
    r'(?i)(^|^\s|[^(]\s+|[^\]]\(\s*)((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'
)
"""
 Regexp for detecting links
 From https://daringfireball.net/2010/07/improved_regex_for_matching_urls
"""

BLANK_REGEX = re.compile(r"^\s*$")
"""
Regexp for detecting blank lines
"""

LIST_REGEX = re.compile(r"^\s*([-*+]|[0-9]\.)")
"""
Regexp for detecting list items
"""


class UrifyExtension(Extension):
    """
    A markdown extension that adds link tags around URIs
    """

    class Impl(Preprocessor):
        def run(self, lines):
            return [URI_REGEX.sub(r"\1[\2](\2)", line) for line in lines]

    def extendMarkdown(self, md):
        md.preprocessors.register(UrifyExtension.Impl(md), "prepend", 10)


class PrependBlankLineExtension(Extension):
    """
    A markdown extension that ensures there is a blank line before the
    first item of each list
    (Otherwise markdown does not interpret it as a proper list)
    """

    class Impl(Preprocessor):
        def run(self, lines):
            result = []
            was_blank = False
            was_list = False
            for line in lines:
                if LIST_REGEX.match(line):
                    if not (was_blank or was_list):
                        # Insert a blank line before start of list
                        result.append("\n")

                    was_blank = False
                    was_list = True
                else:
                    was_list = False
                    was_blank = BLANK_REGEX.match(line)
                result.append(line)
            return result

    def extendMarkdown(self, md):
        md.preprocessors.register(PrependBlankLineExtension.Impl(md), "prepend", 20)


def markdown_to_html(text):
    """Render markdown text to html.

    :param description: Markdown source.
    :type description: string
    :return: Rendered text as HTML
    :rtype: string
    """
    extensions = ["nl2br", UrifyExtension(), PrependBlankLineExtension()]
    return markdown.markdown(text, extensions=extensions)
