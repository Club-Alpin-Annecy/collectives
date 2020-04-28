""" Module handling Markdown rendering.

Markdown is mainly used in event description.
"""
import re
import markdown
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension

# pylint: disable=C0301
URI_REGEX = re.compile(
    r'(?i)(^|^\s|[^(]\s+|[^\]]\(\s*)((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'
)
"""
 Regexp for detecting links.

 From https://daringfireball.net/2010/07/improved_regex_for_matching_urls

 :type: :py:class:`re.Pattern`
"""

BLANK_REGEX = re.compile(r"^\s*$")
"""
Regexp for detecting blank lines

:type: :py:class:`re.Pattern`
"""

LIST_REGEX = re.compile(r"^\s*([-*+]|[0-9]+\.)\s")
"""
Regexp for detecting list items

:type: :py:class:`re.Pattern`
"""


class UrifyExtension(Extension):
    """
    A markdown extension that adds link tags around URIs.
    """

    class Impl(Preprocessor):
        """ A preprocessor for :py:class:`UrifyExtension` """

        def run(self, lines):
            """ Takes all lines and add a link on standalone URL.

            :param lines: All lines where a URL could be found.
            :type lines: list(String)
            :return: Lines with standalone URL replaced by markdown link.
            :rtype: list(String)
            """
            return [URI_REGEX.sub(r"\1[\2](\2)", line) for line in lines]

    def extendMarkdown(self, md):
        """ Fonction that will add the :py:class:`UrifyExtension` to the Markdown
        preprocessor.

        :param md: Markdown processor object.
        :type md: :py:class:`markdown.core.Markdown`
        :return: Nothing
        """
        md.preprocessors.register(UrifyExtension.Impl(md), "urify", 10)


class PrependBlankLineExtension(Extension):
    """
    A markdown extension that ensures there is a blank line before the
    first item of each list.
    (Otherwise markdown does not interpret it as a proper list)
    """

    class Impl(Preprocessor):
        """ A preprocessor for :py:class:`PrependBlankLineExtension` """

        def run(self, lines):
            """Fonction that will  ensures there is a blank line before the
            first item of each list.

            :param lines: All lines where a list could be found.
            :type lines: list(String)
            :return: Lines with an additional blank line before lists.
            :rtype: list(String)
            """
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
        """ Fonction that will add the :py:class:`PrependBlankLineExtension` to the Markdown
        preprocessor.

        :param md: Markdown processor object.
        :type md: :py:class:`markdown.core.Markdown`
        :return: Nothing
        """
        md.preprocessors.register(PrependBlankLineExtension.Impl(md), "prepend", 20)


def markdown_to_html(text):
    """Convert a markdown text to HTML.

    :param text: Markdown text.
    :type text: String
    :return: Converted HTML text.
    :rtype: String

    """

    extensions = ["nl2br", UrifyExtension(), PrependBlankLineExtension()]
    return markdown.markdown(text, extensions=extensions)
