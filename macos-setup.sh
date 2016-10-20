#!/usr/bin/env bash

# install homebrew if we don't have it
# update all homebrew recipes if we do
which -s brew
if [[ $? != 0 ]]  # if exist status of previous command is not 0 (i.e. command failed)
then
    echo "installing homebrew..."
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
else
    echo "updating homebrew..."
    brew update
    brew doctor
fi

PACKAGES=(
    git
    postgresql
    redis
    maven
)

echo "installing packages..."
brew install ${PACKAGES[@]}

echo "cleaning up..."
brew cleanup

echo "starting psql and redis services..."
brew services start postgresql
brew services start redis

if redis-cli ping | grep -q "PONG"
then
    echo "redis installation OK"
else
    echo "problem detected with redis installation"
fi

# create colandr_app user and colandr db for postgresql
if psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='colandr_app'" | grep -q 1
then
    echo "'colandr_app' psql user already exists"
else
    echo "creating 'colandr_app' psql user..."
    createuser --echo --pwprompt --superuser --createdb colandr_app
fi

if psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='colandr'" | grep -q 1
then
    echo "'colandr' psql database already exists"
else
    echo "creating 'colandr' psql database..."
    createdb --echo --encoding=utf8 --host=localhost --port=5432 --username=colandr_app --owner=colandr_app colandr
fi
