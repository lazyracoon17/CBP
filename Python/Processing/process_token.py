#!/usr/bin/env python
"""Wrapper for data collection, processing, and filtering on a provided symbol.

This script will aggregate the following operations provided by the python
processing scripts:

- download_binance_historical_data.py
- historical_data_TF_converter.py
- historical_instances_finder_updater.py
- historical_process_status_of_instances.py
- filter_instances.py

These scripts all generate .csv files which are passed through each script.

All data will be stored in a directory named "Data/" in the working directory
this script is executed from (This can be overridden with arguments).
Each symbol will be stored in it's own sub directory under "Data/".
Within each symbol there will be directories containing the "Candles/"
information, and "Instances/" information for each situation.

Currently only the Binance exchange is supported.
"""

import logging
import argparse
import subprocess
from pathlib import Path

from tqdm import tqdm

import filter_instances

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s')
logger = logging.getLogger('FilterProcess')

defulat_data_dir = Path('./Data/')
default_start_date = '2020-01-01'  # The start date for the data download


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description=f'{__doc__}',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Print verbose output')
    parser.add_argument(
        '-s', '--symbol', dest='symbol',
        help=f'symbol to use, using the Binance API name. E.g. SOLUSDT')
    parser.add_argument(
        '-d', '--data-dir', dest='data_dir', default=defulat_data_dir,
        help=(f'Default root path containing data for all symbols.'))
    parser.add_argument(
        '--start-date', type=str, default=default_start_date,
        help='Start date (YYYY-MM-DD or YYYYMMDD) in UTC')
    parser.add_argument(
        '--direction', dest='direction', default='both',
        help='direction, long or short. Default: both')
    parser.add_argument(
        '--min-diff-percent', dest='min_diff_percent', default=1,
        help='minimum diff percent. Default 1.0')

    args = parser.parse_args()
    if len(args.symbol) <= 3 or args.symbol.isspace():
        parser.error(f'Invalid symbol value provided ("{symbol}")')
    args.data_dir = Path(args.data_dir)

    return args


if __name__ == "__main__":
    args = parse_args()

    start_date = args.start_date

    symbol = args.symbol
    data_dir = args.data_dir
    symbol_dir = data_dir / f'{symbol}-BINANCE'
    candles_dir = symbol_dir / 'Candles'
    instances_dir = symbol_dir / 'Instances/1v1/Unprocessed'
    processed_dir = symbol_dir / 'Instances/1v1/Processed/CompleteSet'
    filtered_dir = symbol_dir / 'Instances/1v1/Processed/Filtered'

    candles_dir.mkdir(parents=True, exist_ok=True)
    instances_dir.mkdir(parents=True, exist_ok=True)

    tqdm.write(
        f'Starting processing pipeline for {symbol} using directory: '
        f'"{candles_dir}"')

    # TODO: Currently the existing script's main() functions setup a lot of
    # global variable dependencies and call functions. These could be
    # refactored into a main that just parses args, then a wrapper
    # function that receives them. This would allow other scripts like this one
    # to call that new intermediary function. And main() would be used when the
    # script is called directly. The main difference is just "who" is providing
    # the python keyword args, cmdline through main() or another script using
    # the wrapper.

    script_path = Path(__file__).absolute().parent

    tqdm.write(f'Starting "download_binance_historical_data.py"...')
    subprocess.run([
        'python',
        str(script_path / 'download_binance_historical_data.py'), '--all',
        '--symbol', symbol, '-d',
        str(candles_dir), '--start-date', args.start_date
    ])

    tqdm.write(f'Starting "download_binance_historical_data.py"...')
    subprocess.run([
        'python',
        str(script_path / 'historical_data_TF_converter.py'), '-p',
        str(candles_dir)
    ])

    tqdm.write(f'Starting "historical_instances_finder_updater.py"...')
    subprocess.run([
        'python',
        str(script_path / 'historical_instances_finder_updater.py'), '-i',
        str(candles_dir), '-o',
        str(instances_dir)
    ])

    tqdm.write(f'Starting "historical_process_status_of_instances.py"...')
    subprocess.run([
        'python',
        str(script_path / 'historical_process_status_of_instances.py'), '-c',
        str(candles_dir), '-i',
        str(instances_dir), '-o',
        str(processed_dir)
    ])

    tqdm.write(f'Completed processing pipeline for {symbol}.')

    default_status = ['Pending', 'Active']
    default_situations = ['all']
    min_diff_percent = 2
    tqdm.write(
        f'Creating filtered CSVs for shorts, longs, and combined using '
        'filters:'
            f'\n    Status: {default_status}'
            f'\n    Situations: {default_situations}'
            f'\n    Min Diff Percent: {min_diff_percent}'
    )
    for direction in ['both', 'short', 'long']:
        outfile = filtered_dir / f'{symbol}_filtered_direction.csv'
        filter_instances.filter_dir_to_csv(
            input_dir=processed_dir, output_file=outfile, direction=direction,
            status=default_status, min_diff_percent=min_diff_percent,
            situations=default_situations)
    tqdm.write(f'Filtering CSVs completed: {filtered_dir}')
    tqdm.write(f'Done downloading, processing, and filtering.')
