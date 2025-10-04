"""Provides filtering capabilities for processed candle break csv files.

The main routine will generate a combined csv of all time frames in the
provided directory.
"""
import logging
import argparse
from typing import Literal
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s')
logger = logging.getLogger('FilterProcess')

VALID_DIRECTIONS = ['both', 'short', 'long']
VALID_SITUATIONS = ['all', '1v1', '1v1+1']


def parse_args():
    """Parse command line arguments and apply defaults."""
    input_dir = Path(
        '../../Data/SOLUSDT-BINANCE/Instances/1v1/Processed/CompleteSet/')
    output_dir = Path(
        '../../Data/SOLUSDT-BINANCE/Instances/1v1/Processed/Filtered/')

    parser = argparse.ArgumentParser(
        description=f'{__doc__}',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Print verbose output')
    parser.add_argument(
        '-i', '--input', dest='input_dir', default=input_dir, help=
        f'Input folder path containing instances CSV files (default: {input_dir})'
    )
    parser.add_argument(
        '-o', '--output', dest='output_dir', default=output_dir,
        help=f'Output folder path for instance files (default: {output_dir})')
    parser.add_argument(
        '-p', '--prompt', action='store_true', default=False, help=(
            'Prompt for paths to be provided. This can still be used with '
            '-i and -o which will use those args for the defaults'))
    parser.add_argument(
        '--direction', dest='direction', default='both',
        help='direction, long or short. Default: both')
    parser.add_argument(
        '--min-diff-percent', dest='min_diff_percent', default=1,
        help='minimum diff percent. Default 1.')

    args = parser.parse_args()
    args.min_diff_percent = float(args.min_diff_percent)
    if args.min_diff_percent < 0.0:
        parser.error('invalid --min-diff-percent, must be >= 0.0')

    if args.direction not in VALID_DIRECTIONS:
        parser.error(
            f'direction ({args.direction} invalid, must be '
            f'{valid_directions})')

    return args


def combine_all_tfs(input_path: Path | str) -> pd.DataFrame:
    """Combine all processed csv files into one DataFrame containing all TFs.

    Arguments:
        input_path: path containing all csvs. A pathlib.Path object is
            expected, but if a string is provided it will be coerced to a Path.

    Returns:
        A pandas.DataFrame with the combined info from all csv files in the
        provided directory.

    Raises:
        FileNotFoundError: The input path does not exist or no .csv files were
        found.

        Other: Error reading the csv files.
    """
    input_path = Path(input_path)
    logger.debug(f'combining all timeframe csvs in dir: {input_path}')
    all_dataframes: list[pd.DataFrame] = []
    combined_dataframes: pd.DataFrame

    if not input_path.exists():
        msg = f'provided directory does not exist ({input_path}).'
        logger.critical(msg)
        raise FileNotFoundError(msg)
    elif not any(input_path.glob('*.csv')):
        msg = f'no .csv files found in provided directory ({input_path})'
        logger.critical(msg)
        raise FileNotFoundError(msg)

    for path in input_path.glob('*.csv'):
        try:
            df = pd.read_csv(path)
        except Exception as e:
            logger.critical(f'error reading csv ({path}) - {e}')
            raise
        all_dataframes.append(df)

    combined_dataframes = pd.concat(all_dataframes, ignore_index=True)

    return combined_dataframes


def filter_instances(
    dataframe: pd.DataFrame,
    direction: Literal['short', 'long', 'both'] = 'both',
    status: list[Literal['Pending', 'Active', 'Completed']] = [],
    min_diff_percent: float = 1.0,
    situations: list[str] = ['all'],
) -> pd.DataFrame:
    """Processes a Dataframe in instances to reduce it based on the options.

    This function receives and returns dataframes to allow it to be imported
    and used elsewhere.

    Arguments:
        dataframe: Pandas Dataframes of processed candle break instances.
        direction: Direction of the position (long, short, both). Default: both.
        status: Instance status, Pending, Active, or Completed. Default: all.
        min_diff_percent: Minimum percent difference from entry to target.
            Default 1.
        situations: Candle break situation; all, 1v1, 1v1+1, etc.
    """
    logger.info(
        f'filtering the provided dataframe for: '
        f'diff percent: >{min_diff_percent}, direction (l/s): {direction}, '
        f'status: {status or "all"}, situations: {situations or "all"}')

    filtered_df = dataframe[dataframe['Status'].isin(status)]

    filtered_df = filtered_df.query(f'diff_percent > {min_diff_percent}')

    if direction.lower() in ['short', 'long']:
        filtered_df = filtered_df[filtered_df['direction'] ==
                                  direction.lower()]

    if situations and 'all' not in situations:
        filtered_df = filtered_df[filtered_df['situation'] in situations]

    logger.debug(f'filtered dataframe:\n{filtered_df}')

    return pd.DataFrame(filtered_df)


def filter_from_dir(input_dir: Path, **kwds):
    """
    """
    dataframes = combine_all_tfs(input_dir)

    filtered_instances = filter_instances(dataframes, **kwds)
    filtered_instances = filtered_instances.drop(
        columns=['fib0_0', 'fib0_5', 'fib_0_5', 'fib_1_0'])


def filter_dir_to_csv(input_dir: Path | str, output_file: Path | str, **kwds):
    input_dir = Path(input_dir)
    output_file = Path(output_file)
    logger.info(f'\nUsing instances directory: "{input_dir}"')
    logger.info(f'The output file will be placed in: "{output_file}"')

    dataframes = combine_all_tfs(input_dir)

    filtered_instances = filter_instances(dataframes, **kwds)
    filtered_instances = filtered_instances.drop(
        columns=['fib0_0', 'fib0_5', 'fib_0_5', 'fib_1_0'])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    filtered_instances.to_csv(output_file, index=False, mode='w')
    logger.info(f'The filtered instances were saved to: {output_file}')


if __name__ == "__main__":
    args = parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if args.prompt:
        input_dir = Path(
            input(
                '\n\rEnter the folder path containing the processed CSV files '
                f'(default: {input_dir}):')) or input_dir
        output_dir = Path(
            input(
                '\n\rEnter the output folder path to save the filtered instance '
                f'CSV files (default: {output_dir}): ')) or output_dir

    output_file = output_dir / 'filtered_instances.csv'
    if args.direction == 'short':
        output_file = output_dir / 'filtered_shorts.csv'
    elif args.direction == 'long':
        output_file = output_dir / 'filtered_longs.csv'

    # default_status = ['Pending', 'Active', 'Completed']
    default_status = ['Pending', 'Active']
    default_situations = ['all']

    filter_dir_to_csv(
        input_dir, output_file, direction=args.direction,
        status=default_status, min_diff_percent=args.min_diff_percent,
        situations=default_situations)
