#!/bin/bash

logfile=$1
csvfile=$2
keywords=$3
index=${4:-1}
max_number=7000

export PATH=$PATH:`pwd`

if [ -z "$logfile" ] || [ -z "$csvfile" ] || [ -z "$keywords" ]; then
  echo "Usage: $0 [logfile] [csvfile] [keywords_file] [index_directory_output]"
  exit 1
fi

# for engine in Google Bing Baidu; do
for engine in Google; do
  cat $keywords | while read key; do
    echo python image_downloader.py --engine $engine --driver chrome_headless --max-number $max_number --num-threads 5 --output images/images_${index} "$key"
    python image_downloader.py --engine $engine --driver chrome_headless --max-number $max_number --num-threads 5 --output images/images_${index} "$key"
    let "index+=1"
  done
done > $logfile

cat $logfile | grep "## OK" | cut -c 9- > $csvfile
