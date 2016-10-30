#!/bin/bash

bin_dir=`dirname "$0"`
bin_dir=`cd "$bin_dir"; pwd`

. $bin_dir/app_env.sh

pid_file="/tmp/$APP_NAME.pid"
#echo $pid_file
pid=0

run_service=0
if [ -e $pid_file ];
then
  pid=`cat $pid_file`
  ps_output=`ps -p $pid -o pid | tail -n +2`
  if [ -z $ps_output ];
  then
    run_service=1
  fi
else
  run_service=1
fi

if [ $run_service == 0 ];
then
  echo "Stopping $APP_NAME Controller..."
  kill $pid
  rm -f $pid_file
else
  echo "$APP_NAME Controller is not running"
fi