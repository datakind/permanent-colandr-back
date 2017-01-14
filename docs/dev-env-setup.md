**Note:** Much of this process can be performed automatically by running the `macos-setup.sh` script at the top level of this directory.


## Set Up System Tools

[Homebrew](http://brew.sh/) installs the stuff you need that Apple didn’t. From a command line (denoted by `$`), enter the following to install Homebrew:

```
$ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

Insert the Homebrew directory at the top of your `PATH` environment variable by adding the following to your `~/.profile` (or `~/.bash_profile`, `~/.zshrc`, etc.) file:

```
export PATH=/usr/local/bin:/usr/local/sbin:$PATH
```

If Homebrew is already installed, just be sure to update it:

```
$ brew update
```

Also install `git`, for version control and (later) access to the app's code:

```
$ brew install git
```


## Set Up PostgreSQL

Install with Homebrew:

```
$ brew install postgresql
```

Or, if already installed,

```
$ brew upgrade postgresql
```

Run `initdb` just once, basically to create the directory structure and such on disk that's needed for creating new databases. Note: The specified path should match the version of Postgres just installed!

```
$ initdb /usr/local/var/postgres9.5 -E utf8
```

You'll need a way to start and stop a local Postgres server from running. To do this _manually_:

```
$ pg_ctl -D /usr/local/var/postgres -l /usr/local/var/postgres/server.log start
$ pg_ctl -D /usr/local/var/postgres stop -s -m fast
```

Or, to do this _automatically_ now (and every time at launch):

```
$ mkdir -p ~/Library/LaunchAgents
$ ln -sfv /usr/local/opt/postgresql/*.plist ~/Library/LaunchAgents
$ launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist
```

Open the system paths file, `/etc/paths`, in a text editor, and move the line `/usr/local/bin` from the bottom of the file to the top (if it wasn't like this already). If you had to make a change to the file, reboot the computer. After rebooting, the command `which psql` command should return `/usr/local/bin/psql`.

Homebrew automatically created a database superuser account with the same login as your current Mac OS account. Let's create a dedicated user named `colandr_app` for connecting to and owning the app's database:

```
$ createuser --echo --pwprompt --superuser --createdb colandr_app
```

You'll be prompted to create a password — be sure to remember it or save it somewhere!

Homebrew also automatically created a database named `postgres` that may be used to log info for administrative tasks such as creating a user. Let's create a new database for this project:

```
$ createdb --echo --encoding=utf8 --host=<HOST> --port=<PORT> --username=colandr_app --owner=colandr_app colandr
```

We're using our `colandr_app` user to create the database, and assigning it as the db's owner.

To access the database through an interactive shell:

```
$ psql --host=<HOST> --port=<PORT> --username=colandr_app --dbname=colandr
```

Outside the Postgres shell, define an environment variable that lets colandr know where the Postgres database is. It's probably best to add it to your `~/.profile` (or `~/.bash_profile`, `~/.zshrc`, etc.) file:

```
$ export COLANDR_DATABASE_URI="postgresql://colandr_app:<DB_PASS>@<DB_HOST>:<DB_PORT>/colandr"
```


## Set Up Redis

Redis is an in-memory data structure store, commonly used as a database, cache, and (as in the case of `colandr`) a message broker. Install it with Homebrew:

```
$ brew install redis
```

Or, if already installed,

```
$ brew upgrade redis
```

You'll need a way to start and stop a local Redis server from running. The second command starts it (and enables autostart for when the computer starts up), the last command stops it (and disables autostart).

```
$ ln -sfv /usr/local/opt/redis/*.plist ~/Library/LaunchAgents
$ launchctl load -w ~/Library/LaunchAgents/homebrew.mxcl.redis.plist
$ launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.redis.plist
```

Once running, do a quick sanity-check to make sure redis is working:

```
$ redis-cli ping
```

If it replies `PONG`, you should be good to go.


## Set Up Colandr

First you'll need access permissions to the GitLab repository — contact DataKind! Then, "clone" the code needed to run the app from its remote repository. Make a new local directory for the repo (if needed) and change your current working directory to it:

```
$ mkdir /path/to/cloned_repo
$ cd /path/to/cloned_repo
$ git clone http://gitlab.datakind.org/conservation-intl/conservation-intl.git
```

This command should create a `conservation-intl` directory, in which the app's code lives.

Now create a few environment variables needed by the app to configure itself and send emails. `COLANDR_APP_DIR` is the location of the `conservation-intl` directory on disk. `COLANDR_SECRET_KEY` acts like an app-wide password, so keep it secret, keep it safe, and keep it _strong_. `COLANDR_PASSWORD_SALT` is also like a password, used by the app when sending custom links in account registration confirmation emails. `COLANDR_MAIL_USERNAME` and `COLANDR_MAIL_PASSWORD` are the credentials for the email account that sends those emails.

```
$ export COLANDR_FLASK_CONFIG="default"
$ export COLANDR_APP_DIR="/path/to/conservation-intl"
$ export COLANDR_SECRET_KEY="<YOUR_SECRET_KEY>"
$ export COLANDR_PASSWORD_SALT="<YOUR_PASSWORD_SALT>"
$ export COLANDR_MAIL_USERNAME="<AN_EMAIL_ADDRESS>"
$ export COLANDR_MAIL_PASSWORD="<THE_CORRESPONDING_PASSWORD>"
```

The `.env.example` file has these environment variables already written out. It may be convenient to copy this file, rename it to `.env`, set the desired variable values, then run `$ source .env`.


## Set Up Python 3

For a fuller guide to everything below, check out [The Hitchhiker's Guide to Python](http://docs.python-guide.org/en/latest/).

Install Python 3 with Homebrew:

```
$ brew install python3
```

You may wish to develop within a virtual environment. (See [here](http://docs.python-guide.org/en/latest/dev/virtualenvs/?highlight=virtualenv) for more information on working within virtual envs.) If so, install with `pip`, then create a project-specific virtual environment:

```
$ pip3 install virtualenv
$ cd /path/to/conservation-intl
$ virtualenv <VENV_NAME>
$ source <VENV_NAME>/bin/activate
```

If you haven't already, change your working directory to your local copy of the repo (see the section above), then install all 3rd-party dependencies upon which the app will rely by:

```
$ cd /path/to/conservation-intl
$ pip3 install "numpy>=1.9"
$ pip3 install -r requirements.txt
```

The app's NLP is built on the `spacy` package, which requires a manual download of model data. After installing it above, run the following commands:

```
$ python3 -m spacy.en.download
$ python3 -c "import spacy; spacy.load('en'); print('OK')"
```

The second command will print "OK" if the download was successful.

You may wish to develop within an IPython interpreter and/or Jupyter Notebook. If so:

```
$ pip3 install ipython jupyter
```

Lastly add the repository directory to your `PYTHONPATH` environment variable by modifying the corresponding line (or adding a new line) in your `~/.profile` (or `~/.bash_profile`, `~/.zshrc`, etc.) file:

```
export PYTHONPATH=/path/to/conservation-intl/:$PYTHONPATH
```
