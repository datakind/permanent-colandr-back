#!/bin/bash
bin_dir=`dirname "$0"`
bin_dir=`cd "$bin_dir"; pwd`
. $bin_dir/stop.sh
. $bin_dir/start.sh