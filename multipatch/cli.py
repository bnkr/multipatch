import argparse, sys, os, yaml, logging
from datetime import datetime as DateTime
import git

class MultiPatchCli(object):
    """Command-line entry point."""
    def __init__(self, argv):
        self.argv = argv
        self.settings = None

    def run(self):
        parser = self.make_parser()
        self.settings = parser.parse_args(self.argv[1:])

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
        tracking = self.get_config()

        repo = git.Repo(self.settings.root)

        # Possibly not necessary?
        for head in repo.heads:
            if head.name == "master":
                head.checkout()
                break

        if repo.active_branch.name != "master":
            self.raise_error("repo could not swtich to master")

        for remote in tracking['remotes']:
            try:
                self.log("{0} exists; set url to {1}", remote['name'], remote['uri'])
                existing = repo.remotes[remote['name']]
                config = existing.config_writer
                config.set('url', remote['uri'])
                del config
            except IndexError:
                # TODO: better error?  __in__ doesn't work properly
                self.log("create remote {0}; set url to {1}", remote['name'], remote['uri'])
                repo.create_remote(remote['name'], remote['uri'])

        for branch in tracking['branches']:
            self.log("create branch {0!r}", branch)
            remote = repo.remotes[branch['origin']]
            # Can't work out how to restrict to just the branch we actually care
            # about but the branches cann't be created until this.
            remote.fetch()

            remote_branch = remote.refs[branch['branch']]

            # Create a tracking branch without checking it out.
            path = ".".join([remote.name, branch['branch']])
            branch = repo.create_head(path, commit=remote_branch.commit)
            branch.set_tracking_branch(remote_branch)

        return 0

    def run_log_command(self):
        """Print the logs of the tracked branches in chronological order."""
        tracking = self.get_config()
        repo = git.Repo(self.settings.root)

        wip = []
        for branch in tracking['branches']:
            # TODO: Why not just use the remote branch ref?
            remote = repo.remotes[branch['origin']]
            branch_name = ".".join([remote.name, branch['branch']])
            ref = repo.refs[branch_name]

            commits = git.objects.Commit.iter_items(repo, branch_name)
            try:
                top = commits.next()
            except StopIteration:
                continue

            wip.append({'ref': ref, 'top': top, 'iter': commits})

        # Sort in ascending order of commit date.  Print the highest (iow most
        # recent).  If we run out of commits to print then remove from the next
        # iteration.
        while wip:
            wip.sort(key=lambda entry: entry['top'].committed_date, reverse=False)

            current = wip[-1]
            self.print_pretty_log_message(ref=current['ref'], commit=current['top'])

            try:
                current['top'] = current['iter'].next()
            except StopIteration:
                wip.pop()

        return 0

    def print_pretty_log_message(self, ref, commit):
        print commit
        print ref.name
        print DateTime.fromtimestamp(commit.committed_date)
        print commit.message.strip()
        print commit.summary.strip()
        print

    def get_config(self):
        root = self.settings.root
        # TODO: Wrong if the repo is bare, but not that wrong.
        config = os.path.join(root, ".git", "multipatch.yml")
        if not os.path.exists(config):
            self.raise_error("no such file: {0}", config)

        with open(config) as io:
            return yaml.load(io.read())

    def make_parser(self):
        parser = argparse.ArgumentParser()
        commands = parser.add_subparsers(dest="command")
        create = commands.add_parser("create")
        create.add_argument('root')
        create = commands.add_parser("log")
        create.add_argument('root')
        return parser

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
