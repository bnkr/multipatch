MultiPatch
==========

Read git logs from multiple git branches (possibly from different remotes) in
one go.  The intended use is to view histroies from several unmerged and
possibly conflicting repositories chronologically.

(Optional) Get Dependencies
---------------------------

Using pbundle, you can get locked dependencies like ruby's bundler or php's
composer::

  $ python pbootstrap.py
  $ ./pbundle_modules/bin/pbundle install
  $ ./python_modules/bin/multipatch --help

Alternatively you can just ``pip install -r requirements.txt`` as you normally
would.

Creating an Environment
-----------------------

Create an empty git repository in ``_root`` (name can be your choice) and add
the following configuration to ``_root/.git/multipatch.yml``.

Configure like this::

  remotes:
  - name: pbundle
    uri: https://github.com/bnkr/pbundle.git
  - name: craftrun
    uri: https://github.com/bnkr/craftrun.git
  branches:
  - remote: pbundle
    branch: master
  - remote: craftrun
    branch: master
  - branch: pants

The ``create`` command will do this::

  $ ./python_modules/bin/python multipatch/cli.py create  _root
  2015-08-04 17:12:51 INFO multipatch: pbundle exists; set url to https://github.com/bnkr/pbundle.git
  2015-08-04 17:12:51 INFO multipatch: craftrun exists; set url to https://github.com/bnkr/craftrun.git
  2015-08-04 17:12:51 INFO multipatch: create branch {'remote': 'pbundle', 'branch': 'master'}
  2015-08-04 17:12:52 INFO multipatch: create branch {'remote': 'craftrun', 'branch': 'master'}
  2015-08-04 17:12:53 INFO multipatch: skip local-only branch {'branch': 'pants'}

In more detail, the following is happening:

* create/update a remote for each of the name/uri combinations in the
  ``remotes`` section.

* create a local branch ``remote.branch`` for reach remote/branch combination in
  the ``branches`` section.

* skip any branch which doesn't have a ``remote`` listed.

Viewing Logs
------------

Given the same configuration::

  $ ./python_modules/bin/python multipatch/cli.py log  _root

Logs of each listed in ``branches`` will be displayed in chronological order.

You can log without using ``create`` if you're prepared to manage your branches
manually.  The ``log`` operation does not need the branches to be local but it
does need the remotes to be configured properly.

More
----

See the help text and read the code.
