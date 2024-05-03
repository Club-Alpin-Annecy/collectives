""" Unit test on :py:mod:`collectives.utils.misc` functions. """

from collectives.utils import misc


def test_sanitize_file_name():
    """Test simple date format"""

    assert misc.sanitize_file_name("test-2.txt") == "test-2.txt"
    assert misc.sanitize_file_name(".test") == ".test"
    assert misc.sanitize_file_name("/etc/passwd") == "_etc_passwd"
    assert (
        misc.sanitize_file_name("Test : collectives.xlsx") == "Test _ collectives.xlsx"
    )
    assert misc.sanitize_file_name("ça à été forêt.txt") == "ça à été forêt.txt"
