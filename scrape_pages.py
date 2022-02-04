import sys
import requests
import argparse
import os
import csv

from retry import retry
from pathlib import Path


def read_csv(filename):
    rows = []
    with open(filename) as f:
        csv_reader = csv.reader(f, delimiter=',')
        for row in csv_reader:
            rows.append(row)

    return rows


@retry(Exception, tries=3, delay=1, backoff=2)
def scrape_page(endpoint):
    return requests.get(endpoint).text


def scrape(csv_file, dest_dir):
    for row in csv_file:
        # get relative directory e filename
        rel_dir, fname = os.path.split(row[0])
        # get filename
        fname = os.path.splitext(fname)[0]
        # destination directory
        dname = os.path.join(dest_dir, rel_dir)
        # build dest filename
        dest_fname = os.path.join(dname, '{}.html'.format(fname))
        # make directory
        Path(dname).mkdir(parents=True, exist_ok=True)
        # get page
        try:
            page = scrape_page(row[2])
            with open(dest_fname, 'w') as f:
                f.write(page)
            yield dest_fname
        except Exception:
            pass


def main(argv):
    parser = argparse.ArgumentParser(description="Page scraper")
    parser.add_argument("csv_file", type=str,
                        help='csv file resulting from the search')
    parser.add_argument("dest_dir", type=str,
                        help='where save scraped images')
    args = parser.parse_args(args=argv)

    csv_file = read_csv(args.csv_file)
    for filename in scrape(csv_file, args.dest_dir):
        print(filename)


if __name__ == '__main__':
    main(sys.argv[1:])
