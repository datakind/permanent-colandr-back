#!/bin/bash

bin_dir=`dirname "$0"`
bin_dir=`cd "$bin_dir"; pwd`
#echo $bin_dir

. $bin_dir/app_env.sh

pid_file="/tmp/$APP_NAME.pid"
#echo $pid_file

JAVA_OPT="-Xmx4g"

curr_dir=`dirname $0`
APP_HOME="$curr_dir/.."
export APP_HOME=`cd $APP_HOME; pwd`
export bin_dir="$APP_HOME/bin"
export config_dir="$APP_HOME/config"

APP_JAR="$APP_HOME/target/$APP_NAME-$APP_VERSION.jar"
#echo $APP_JAR

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
  echo "Controller is already running @ $pid"
else
  echo "Starting Controller Service...  version $APP_VERSION"
  nohup java $JAVA_OPT -cp $config_dir:$APP_JAR org.datakind.ci.pdfestrian.api.API &
  echo $! > $pid_file
  sleep 1;
fi
