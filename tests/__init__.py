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

        utf8_bytes = b"Blah blah \xc2\xa3"

        author = Author(name="some guy")
        commit = Commit(hexsha="a" * 32,
                        summary=utf8_bytes,
                        author=author,
                        committed_date=time.time())

        io = StringIO()
        with redirect_stdout(to=io):
            cli.print_pretty_log_message(ref=ref, commit=commit)

        printed = io.getvalue().encode("utf-8")
        expected = b'aaaaaa repo/master SG Blah blah \xc2\xa3'
        self.assertIn(expected, printed)
