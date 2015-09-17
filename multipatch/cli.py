import argparse, sys, os, yaml, logging, errno
from datetime import datetime as DateTime
import git

class MultiPatchCli(object):
    """Command-line entry point."""
    def __init__(self, argv):
        self.argv = argv
        self.settings = None

    def run(self):
        parser = self.make_parser()
        self.settings = self.parse_args(parser)

        self.logger = logging.getLogger("multipatch")
        message_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'
        time_format = "%Y-%m-%d %H:%M:%S"
        logging.basicConfig(level=logging.INFO, format=message_format,
                            datefmt=time_format)

        command_method = 'run_{0}_command'.format(self.settings.command)
        command = getattr(self, command_method, None)
        try:
            return command()
        except self.CliError as ex:
            sys.stderr.write(unicode(ex))
            sys.stderr.write("\n")
            return 1

    def run_create_command(self):
        """Configure git's remotes and branches to have the configured remote
        repositories and some non-checked out branches."""
        repo, tracking = self.get_config()

        # Possibly not necessary?
        for head in repo.heads:
            if head.name == "master":
                head.checkout()
                break

        if repo.active_branch.name != "master":
            self.raise_error("repo could not swtich to master")

        fetched = set()

        def fetch_remote(remote):
            if remote.name not in fetched:
                self.log("fetching remote {0}", remote.name)
                remote.fetch()
                fetched.add(remote.name)

        for remote in tracking['remotes']:
            # Does not seem to be a check.
            try:
                existing = repo.remotes[remote['name']]
            except IndexError:
                existing = None

            if existing:
                self.log("{0} exists; set url to {1}", remote['name'], remote['uri'])
                config = existing.config_writer
                config.set('url', remote['uri'])
                del config
            else:
                self.log("create remote {0}; set url to {1}", remote['name'], remote['uri'])
                repo.create_remote(remote['name'], remote['uri'])

            if self.settings.fetch or not tracking['branches']:
                fetch_remote(repo.remotes[remote['name']])

        for branch in tracking['branches']:
            if 'remote' not in branch:
                self.log("skip local-only branch {0!r}", branch)
                continue

            self.log("create branch {0!r}", branch)
            remote = repo.remotes[branch['remote']]

            # The branches cann't be created until this.
            if remote.name not in fetched:
                fetch_remote(remote)

            remote_branch = remote.refs[branch['branch']]

            # Create a local tracking branch without checking it out.  This is
            # not actually all that useful for logging but can be useful if you
            # want to view the actual source.
            path = ".".join([remote.name, branch['branch']])
            branch = repo.create_head(path, commit=remote_branch.commit)
            branch.set_tracking_branch(remote_branch)

        return 0

    def run_log_command(self):
        """Print the logs of the tracked branches in chronological order."""
        try:
            branches = self.get_branches_to_log()
            self.print_logs_chronologically(branches)
            return 0
        except KeyboardInterrupt:
            # Avoid spammy exception when we quit in the middle.
            return 0

    def get_branches_to_log(self):
        """Initialise iterators for commits on each branch we want to track."""
        repo, tracking = self.get_config_for_logging()
        wip = []
        for branch in tracking['branches']:
            if 'remote' in branch:
                remote = repo.remotes[branch['remote']]
                ref = remote.refs[branch['branch']]
            else:
                ref = repo.branches[branch['branch']]

            commits = git.objects.Commit.iter_items(repo, ref.name)
            try:
                top = commits.next()
            except StopIteration:
                continue

            wip.append({'ref': ref, 'top': top, 'iter': commits})

        return wip

    def print_logs_chronologically(self, wip):
        """
        Sort in ascending order of commit date.  Print the highest (iow most
        recent).  If we run out of commits to print then remove from the next
        iteration.
        """
        last_date = None

        while wip:
            wip.sort(key=lambda entry: entry['top'].committed_date, reverse=False)

            current = wip[-1]

            this_date = DateTime.fromtimestamp(current['top'].committed_date).date()

            should_print = this_date != last_date
            if self.settings.split_days and this_date != last_date:
                print("On {0}:".format(this_date.isoformat()))

            last_date = this_date

            try:
                self.print_pretty_log_message(ref=current['ref'], commit=current['top'])
            except IOError as ex:
                if ex.errno == errno.EPIPE:
                    return
                else:
                    raise

            try:
                current['top'] = current['iter'].next()
            except StopIteration:
                wip.pop()

        return

    def print_pretty_log_message(self, ref, commit):
        words = commit.author.name.split(' ')
        initials = "".join([word[0].upper() for word in words])
        print DateTime.fromtimestamp(commit.committed_date), commit.hexsha[0:6], \
                ref.name, initials, commit.summary[0:90].strip()

        if self.settings.stat and commit.stats.files:
            for path, change in commit.stats.files.iteritems():
                print "  -{0} +{1}".format(change['deletions'], change['insertions']).ljust(10), path

        if self.settings.patch:
            diffs = commit.diff()
            if diffs:
                print

            for diff in diffs:
                print diff
                print

    def get_config(self):
        config, looked_in = self.get_config_file()
        if not config:
            self.raise_error("no such file: {0}", looked_in)

        with open(config) as io:
            tracking = yaml.load(io.read())
            return git.Repo(self.settings.root), tracking

    def get_config_for_logging(self):
        """Use config or git branches and whatnot to find some things to log."""
        ignore_config = [self.settings.everything, self.settings.all_masters,
                         self.settings.all_remotes]
        if True not in ignore_config:
            repo, tracking = self.get_config()
            return repo, self.filter_branches(tracking)

        repo = git.Repo(self.settings.root)

        remotes = self.find_logables_from_remotes(repo)
        locals = self.find_logables_from_locals(repo)

        tracking = {}
        tracking['branches'] = remotes + locals

        return repo, self.filter_branches(tracking)

    def find_logables_from_locals(self, repo):
        logables = []
        for branch in repo.branches:
            if self.settings.everything:
                logables.append({'branch': branch.name, 'ref': branch})

        return logables

    def find_logables_from_remotes(self, repo):
        logables = []
        for remote in repo.remotes:
            for ref in remote.refs:
                logable = {
                    'remote': remote.name,
                    'branch': ref.name.replace(remote.name + "/", ''),
                    'ref': ref,
                }

                if self.settings.all_remotes or self.settings.everything:
                    logables.append(logable)
                elif logable['branch'] == "master" and self.settings.all_masters:
                    logables.append(logable)

        return logables

    def filter_branches(self, tracking):
        """Remove stuff excluded with -x."""
        filtered = []
        for entry in tracking['branches']:
            skip = False
            for exclude in self.settings.exclude:
                name = entry.get('remote', '') + "/" + entry['branch']
                if exclude in name:
                    skip = True

            if not skip:
                filtered.append(entry)

        return {'branches': filtered}

    def get_config_file(self):
        looked_in = [
            os.path.join(self.settings.root, ".git", "multipatch.yml"),
        ]

        for path in looked_in:
            if os.path.exists(path):
                return path, looked_in

        return None, looked_in

    def make_parser(self):
        parser = argparse.ArgumentParser()
        commands = parser.add_subparsers(dest="command")
        create = commands.add_parser("create")
        create.add_argument('root')
        create.add_argument('-f', '--fetch', action='store_true',
                            help="Fetch remotes we aren't using for branches.")

        log = commands.add_parser("log")
        log.add_argument('root', nargs="?", default=os.getcwd())
        log.add_argument("-m", "--all-masters", action="store_true",
                          help="Show logs from all remotes branches named 'master'.")
        log.add_argument("-A", "--all-remotes", action="store_true",
                          help="Show logs from all remotes.")
        log.add_argument("-e", "--everything", action="store_true",
                          help="Show logs from all remotes.")
        log.add_argument("-x", "--exclude", action='append', default=[],
                          help="Exclude ref names matching.")
        log.add_argument("-s", "--stat", action='store_true',
                          help="Show stat.")
        log.add_argument("-p", "--patch", action='store_true',
                          help="Show patch.")
        log.add_argument("-d", "--split-days", action='store_true',
                          help="Print a header when the day changes.")
        return parser

    def parse_args(self, parser):
        settings = parser.parse_args(self.argv[1:])
        return settings

    def log(self, message, *parts, **kparts):
        message = message.format(*parts, **kparts)
        self.logger.info(message)

    class CliError(Exception):
        pass

    def raise_error(self, message, *parts, **kparts):
        error = message.format(*parts, **kparts)
        raise Exception(error)

if __name__ == "__main__":
    sys.exit(MultiPatchCli(sys.argv).run())
