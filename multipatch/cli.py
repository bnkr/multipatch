import argparse, sys, os, yaml, logging
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
        root = self.settings.root

        # TODO: Wrong if the repo is bare, but not that wrong.
        config = os.path.join(root, ".git", "multipatch.yml")
        if not os.path.exists(config):
            self.raise_error("no such file: {0}", config)

        repo = git.Repo(root)
        for head in repo.heads:
            if head.name == "master":
                head.checkout()
                break

        if repo.active_branch.name != "master":
            self.raise_error("repo could not swtich to master")

        with open(config) as io:
            tracking = yaml.load(io.read())

        for remote in tracking['remotes']:
            try:
                self.log("{0} exists; set url to {1}", remote['name'], remote['uri'])
                existing = repo.remotes[remote['name']]
                config = existing.config_writer
                config.set('url', remote['uri'])
                del config
            except IndexError:
                self.log("create remote {0}; set url to {1}", remote['name'], remote['uri'])
                repo.create_remote(remote['name'], remote['uri'])

        for branch in tracking['branches']:
            print branch

        return 0

    def make_parser(self):
        parser = argparse.ArgumentParser()
        commands = parser.add_subparsers(dest="command")
        create = commands.add_parser("create")
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
