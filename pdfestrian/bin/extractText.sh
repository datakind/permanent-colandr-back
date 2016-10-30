#!/bin/bash
export BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export APP_HOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )"
. $BIN_DIR/app_env.sh

java -cp $APP_HOME/target/$APP_NAME-$APP_VERSION.jar org.datakind.ci.pdfestrian.pdfExtraction.extractText "$@"
