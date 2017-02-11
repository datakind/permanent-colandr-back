#!/bin/bash 
bin_dir=`dirname "$0"`
bin_dir=`cd "$bin_dir"; pwd`
echo "working in $bin_dir"
cd $bin_dir

celery multi restart worker -A "celery_worker.celery"

pid_file="colandr.pid"
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
  echo "gunicorn running pid: $pid"
  echo "Stopping gunicorn"
  kill $pid
  sleep 5
  echo "restarting gunicorn"
else
  echo "starting gunicorn"
fi

gunicorn --config=gunicorn_config.py gunicorn_runserver:app --log-file=colandr.log
sleep 5
echo "gunicorn now running pid: `cat colandr.pid`" 
