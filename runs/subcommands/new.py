# stdlib
from argparse import ArgumentParser
from datetime import datetime
import itertools
from typing import Iterator, List

# first party
from runs.command import Command
from runs.logger import UI
from runs.transaction.transaction import Transaction
from runs.util import PurePath, interpolate_keywords


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'new',
        help='Start a new run.',
        epilog='When there are multiple paths/subcommands/descriptions, '
               'they get collated. If there is one path but multiple subcommands, '
               'each path gets appended with a number. Similarly if there is one '
               'description, it gets broadcasted to all paths/subcommands.')
    assert isinstance(parser, ArgumentParser)

    parser.add_argument(
        '--path',
        dest='paths',
        action='append',
        type=PurePath,
        help='Unique path for each run. '
             'Number of paths and number of subcommands must be equal.',
        metavar='PATH')
    parser.add_argument(
        '--command',
        dest='commands',
        action='append',
        type=str,
        help='Command to be sent to TMUX for each path.'
             'Number of paths and number of subcommands must be equal.',
        metavar='COMMAND')
    parser.add_argument(
        '--description',
        dest='descriptions',
        action='append',
        help='Description of this run. Explain what this run was all about or '
             'write whatever your heart desires. If this argument is `commit-message`,'
             'it will simply use the last commit message.')
    parser.add_argument(
        '--prefix',
        type=str,
        help="String to prepend to all main subcommands, for example, sourcing a "
             "virtualenv")
    parser.add_argument(
        '--flag',
        '-f',
        default=[],
        action='append',
        help="directories to create and sync automatically with each run")
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


@Transaction.wrapper
def cli(prefix: str, paths: List[PurePath], commands: List[str], flags: List[str],
        logger: UI, descriptions: List[str], transaction: Transaction, *args, **kwargs):
    n = len(commands)
    if not len(paths) in [1, n]:
        logger.exit('There must either be 1 or n paths '
                    'where n is the number of subcommands.')

    if not len(descriptions) in [0, 1, n]:
        logger.exit('There must either be 1 or n descriptions '
                    'where n is the number of subcommands.')

    iterator = enumerate(itertools.zip_longest(paths, commands, descriptions))
    for i, (path, command, description) in iterator:
        if path is None:
            if n == 1:
                path = PurePath(paths[0])
            else:
                path = PurePath(paths[0], str(i))
        if len(descriptions) == 0:
            description = 'Description not given.'
        if len(descriptions) == 1:
            description = descriptions[0]

        new(command=Command(prefix=prefix,
                            positional=command,
                            nonpositional=flags,
                            path=path),
            description=description,
            path=path,
            transaction=transaction)


def new(command, description, path, transaction):
    bash = transaction.bash
    if description is None:
        description = ''
    if description == 'commit-message':
        description = bash.cmd('git log -1 --pretty=%B'.split())
    if path in transaction.db:
        transaction.remove(path)
    transaction.add_run(
        path=path,
        command=command,
        commit=bash.last_commit(),
        datetime=datetime.now().isoformat(),
        description=description)


def build_command(command: str, path: PurePath, prefix: str, flags: Iterator[str]) -> str:
    if prefix:
        command = f'{prefix} {command}'
    flags = ' '.join(interpolate_keywords(path, f) for f in flags)
    if flags:
        command = f"{command} {flags}"
    return command