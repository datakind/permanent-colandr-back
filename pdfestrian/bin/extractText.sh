#!/bin/bash
export BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export APP_HOME="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd .. && pwd )"
export APP_NAME="pdfestrian"
export VERSION="0.0.1-SNAPSHOT"
#echo $APP_HOME
java -cp $APP_HOME/target/$APP_NAME-$VERSION-jar-with-dependencies.jar org.datakind.ci.pdfestrian.pdfExtraction.extractText "$@"
