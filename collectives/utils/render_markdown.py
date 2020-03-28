import re
import markdown
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension

# Urify links
# From https://daringfireball.net/2010/07/improved_regex_for_matching_urls
# pylint: disable=C0301
URI_REGEX = re.compile(
    r'(?i)(^|^\s|[^(]\s+|[^\]]\(\s*)((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'
)

BLANK_REGEX = re.compile(r"^\s*$")
LIST_REGEX = re.compile(r"^\s*([-*+]|[0-9]\.)")


class Urify(Preprocessor):
    def run(self, lines):
        return [URI_REGEX.sub(r"\1[\2](\2)", line) for line in lines]


class UrifyExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(Urify(md), "prepend", 10)


class PrependBlankLine(Preprocessor):
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


class PrependBlankLineExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(PrependBlankLine(md), "prepend", 20)


def markdown_to_html(text):
    extensions = ["nl2br", UrifyExtension(), PrependBlankLineExtension()]
    return markdown.markdown(text, extensions=extensions)
