import sys
from unittest import TestCase
from multipatch.cli import MultiPatchCli
from StringIO import StringIO
from contextlib import contextmanager
from datetime import datetime as DateTime
import git
import time
from collections import namedtuple


@contextmanager
def redirect_stdout(to):
    old, sys.stdout = sys.stdout, to
    try:
        yield to
    finally:
        sys.stdout = old


class CliTest(TestCase):
    def test_printing_commit_handles_encoding(self):
        Settings = namedtuple('Settings', ['stat', 'patch'])

        cli = MultiPatchCli([])
        cli.settings = Settings(stat=False, patch=False)

        Ref = namedtuple('Ref', ['name'])
        Author = namedtuple("Author", ['name'])
        Commit = namedtuple('Commit', ['summary', 'hexsha', 'author', 'committed_date'])
        ref = Ref(name="repo/master")

        author = Author(name="some guy")

        unicode_bits = u"aaaaaa repo/master SG Blah blah \u00a3"
        commit = Commit(hexsha="a" * 32,
                        summary=unicode_bits,
                        author=author,
                        committed_date=time.time())

        io = StringIO()
        with redirect_stdout(to=io):
            cli.print_pretty_log_message(ref=ref, commit=commit)

        # Important bit here: we must have encoded the output becuase the print
        # function doesn't do it when we are piping stdout.  Hard to catch this
        # one.
        printed = io.getvalue()
        expected = b'aaaaaa repo/master SG Blah blah \xc2\xa3'
        self.assertIn(expected, printed)
