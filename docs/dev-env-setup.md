## Set Up System Tools

[Homebrew](http://brew.sh/) installs the stuff you need that Apple didn’t. From a command line (denoted by `$`), enter the following:

```
$ /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

Insert the Homebrew directory at the top of your `PATH` environment variable by adding the following to your `~/.profile` (or `~/.bash_profile`, `~/.zshrc`, etc.) file:

```
export PATH=/usr/local/bin:/usr/local/sbin:$PATH
```

Also install `git`, for version control and (later) access to the app's code:

```
$ brew install git
```


## Set Up PostgreSQL

Install with Homebrew:

```
$ brew update && brew install postgres
```

Or, if already installed,

```
$ brew update && brew upgrade postgres
```

Run `initdb` just once, basically to create the directory structure and such on disk that's needed for creating new databases. Note: The specified path should match the version of Postgres just installed!

```
$ initdb /usr/local/var/postgres9.5 -E utf8
```

To _manually_ start and stop a local Postgres server from running, use

```
$ pg_ctl -D /usr/local/var/postgres -l /usr/local/var/postgres/server.log start
$ pg_ctl -D /usr/local/var/postgres stop -s -m fast
```

Or to _automatically_ start a Postgres server (now and) at launch:

```
$ mkdir -p ~/Library/LaunchAgents
$ ln -sfv /usr/local/opt/postgresql/*.plist ~/Library/LaunchAgents
$ launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist
```

Open the system paths file, `/etc/paths`, in a text editor, and move the line `/usr/local/bin` from the bottom of the file to the top (if it wasn't like this already). If you had to make a change to the file, reboot the computer. After rebooting, the command `which psql` command should return `/usr/local/bin/psql`.

Homebrew automatically created a database superuser account with the same login as your current Mac OS account. Let's create a dedicated user named `app` for connecting to and owning the app's database:

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

While we're in the interactive shell, let's create the `pgcrypto` extension for secure password storage and `intarray` extension for integer array handling (**Note:** This may no longer be necessary, but it can't hurt!):

```
=# CREATE EXTENSION "pgcrypto";
=# CREATE EXTENSION "intarray";
```

Lastly, after exiting the postgres shell, define two environment variables used when configuring the API on the server. It's probably best to add them to your `~/.profile` (or `~/.bash_profile`, `~/.zshrc`, etc.) file. The first variable lets the API know where the database is; the second variable acts like an app-wide password, so keep it secret, keep it safe, and keep it _strong_.

```
$ export SQLALCHEMY_DATABASE_URI="postgresql://colandr_app:<DB_PASS>@<DB_HOST>:<DB_PORT>/colandr"
$ export COLANDR_SECRET_KEY="<YOUR_SECRET_KEY>"
```


## Get the App Code

First you'll need access permissions to the GitLab repository — contact DataKind! Then, "clone" the code needed to run the app from its repository hosted on GitLab. Make a new local directory for the repo (if needed) and change your current working directory to it:

```
$ mkdir /path/to/cloned_repo
$ cd /path/to/cloned_repo
$ git clone http://gitlab.datakind.org/conservation-intl/conservation-intl.git
```

This command should create a `conservation-intl` directory, in which the app's code lives.


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
$ pip3 install -r requirements.txt
```

You may wish to develop within an IPython interpreter and/or Jupyter Notebook. If so:

```
$ pip3 install ipython jupyter
```

Lastly add the repository directory to your `PYTHONPATH` environment variable by modifying the corresponding line (or adding a new line) in your `~/.profile` (or `~/.bash_profile`, `~/.zshrc`, etc.) file:

```
export PYTHONPATH=/path/to/conservation-intl/:$PYTHONPATH
```
