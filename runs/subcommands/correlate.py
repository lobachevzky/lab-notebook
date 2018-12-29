# stdlib
import math
from pathlib import Path
import re
from typing import Callable, Dict, List, Optional

# first party
from runs.arguments import add_query_args
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import PurePath


def add_subparser(subparsers):
    parser = subparsers.add_parser('correlate', help='Rank args by Pearson correlation.')
    add_query_args(parser, with_sort=False)
    parser.add_argument(
        '--value-path',
        required=True,
        type=Path,
        help='The command will look for a file at this path containing '
        'a scalar value. It will calculate the pearson correlation between '
        'args and this value. The keyword <path> will be replaced '
        'by the path of the run.')
    return parser


@DataBase.open
@DataBase.query
def cli(logger: Logger, runs: List[RunEntry], value_path: Path, *_, **__):
    print('Analyzing the following runs', *[r.path for r in runs], sep='\n')
    logger.print(*strings(runs=runs, value_path=value_path), sep='\n')


def strings(*args, **kwargs):
    cor = correlations(*args, **kwargs)
    keys = sorted(cor.keys(), key=lambda k: cor[k])
    return [f'{cor[k]}, {k}' for k in keys]


def get_args(command: str) -> List[str]:
    return re.findall('(?:[A-Z]*=\S* )*\S* (\S*)', command)


def correlations(
        runs: List[RunEntry],
        value_path: Path,
) -> Dict[str, float]:
    def mean(f: Callable) -> float:
        try:
            return sum(map(f, runs)) / float(len(runs))
        except ZeroDivisionError:
            return math.nan

    def get_value(path: PurePath) -> Optional[float]:
        try:
            with Path(str(value_path).replace('<path>', str(path))).open() as f:
                return float(f.read())
        except (ValueError, FileNotFoundError):
            return

    runs = [r for r in runs if get_value(r.path) is not None]
    value_mean = mean(lambda run: get_value(run.path))
    value_std_dev = math.sqrt(mean(lambda run: (get_value(run.path) - value_mean)**2))

    def get_correlation(arg: str) -> float:
        def contains_arg(run: RunEntry) -> float:
            return float(arg in get_args(run.command))

        if sum(map(contains_arg, runs)) == len(runs):
            return None

        arg_mean = mean(contains_arg)

        covariance = mean(
            lambda run: (contains_arg(run) - arg_mean) * (get_value(run.path) - value_mean)
        )

        std_dev = math.sqrt(mean(lambda run: (contains_arg(run) - arg_mean)**2))

        # return covariance
        denominator = std_dev * value_std_dev
        if denominator:
            return covariance / denominator
        else:
            return math.inf

    args = {arg for run in runs for arg in get_args(run.command)}
    correlations = {arg: get_correlation(arg) for arg in args}
    return {
        arg: correlation
        for arg, correlation in correlations.items() if correlation is not None
    }
