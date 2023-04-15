**Note:** Much of this process can be performed automatically by running the `macos-setup.sh` script at the top level of this directory.


## Set Up System Tools

If this computer has not previously been used for software development, you may need to install Xcode's command line tools, which includes a bunch of low-level tools that other packages rely upon. From the command line, run:

```shell
$ xcode-select --install
```

Next, if you don't already have it, you'll needs [Homebrew](http://brew.sh), which installs the stuff that Apple didn’t:

```shell
$ /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Add Homebrew's executable directory to your `PATH` environment variable by opening your shell's rc file (usually `~/.zshrc` if you're using `zsh`, `~/.bashrc` if you're using `bash`) in your preferred text editor, then adding the following line:

```
export PATH=/usr/local/bin:$PATH
```

Load this change by running `$ source [FILE]` on the file you just modified or simply opening a new terminal window. Whether Homebrew was already or newly installed, be sure to update it and give it a check-up:

```shell
$ brew update
$ brew doctor
```


## Set Up PostgreSQL

Colandr's back-end database, [PostgreSQL](https://www.postgresql.org) (v9.X, for now?), can be installed with Homebrew:

```shell
$ brew install postgresql@9.5
```

**Note:** In recent versions of Homebrew, this version has been disabled, and the earliest supported formula is `postgresql@10`. We probably have to upgrade the production database to this or a more recent version in order to continue support.

Be sure to read and heed the information printed out at the end of the installation process! Homebrew should automatically run `initdb` to create the directory structure and such on disk that's needed for creating new dbs (i.e. `initdb --locale=C -E UTF-8 /usr/local/var/postgresql@X`). If you have multiple versions of Postgres isntalled -- check using `brew search postgresql` -- you may have to overwrite the existing linked version:

```shell
$ brew link --overwrite [--dry-run] postgresql@X
```

You'll need a way to start and stop a local Postgres server from running (which includes stopping a different version before starting the version just installed). To do so in the background, use `brew services {start|stop} postgresql@X`. Or to do this manually without Homebrew:

```shell
$ pg_ctl -D '/usr/local/var/postgresql@X' -l logfile start
$ pg_ctl -D '/usr/local/var/postgresql@X' stop -s -m fast
```

Homebrew automatically created a database superuser account with the same login as your current Mac OS account. Let's create a dedicated user named `colandr_app` for connecting to and owning the app's database:

```shell
$ createuser --echo --pwprompt --superuser --createdb colandr_app
```

You'll be prompted to create a password -- be sure to remember it or save it somewhere!

Homebrew also automatically created a database named `postgres` that may be used to log info for administrative tasks such as creating a user. Let's create a new database for this project with `colandr_app` as its owner:

```shell
$ createdb --echo --encoding=utf8 --host=<DB_HOST> --port=<DB_PORT> --username=colandr_app --owner=colandr_app colandr
```

Note that the default port is 5432 and host is "localhost". Now, to access the database through an interactive shell, run:

```shell
$ psql --host=<DB_HOST> --port=<DB_PORT> --username=colandr_app --dbname=colandr
```

Outside the Postgres shell, define an environment variable that lets colandr know where the Postgres database is. It's probably best to add it to your `~/.profile` (or `~/.bashrc`, `~/.zshrc`, etc.) file:

```shell
$ export COLANDR_DATABASE_URI="postgresql://colandr_app:<USER_PASSWORD>@<DB_HOST>:<DB_PORT>/colandr"
```


## Set Up Redis

[Redis](https://redis.io) is an in-memory data structure store that colandr uses as a message broker. Install it with Homebrew:

```shell
$ brew install redis
```

**Note:** Unlike PostgreSQL, redis doesn't support installing specific versions via Homebrew -- instead, you always install the latest version. That's a bummer! The version originally run in production was probably v3.2, but as of 2023 the latest version is v7.0. Redis is careful about backwards compatibility, but beware any breaking changes across the major versions! If this is an issue, consider installing redis from source.

As before, you'll need a way to start and stop a local Redis server. You can do this in the background via `brew services {start|stop} redis`. Alternatively, you can have redis start automatically when the system boots up using `launchtctl`, like so:

```shell
$ ln -sfv /usr/local/opt/redis/*.plist ~/Library/LaunchAgents
$ launchctl load -w ~/Library/LaunchAgents/homebrew.mxcl.redis.plist
$ launchctl unload ~/Library/LaunchAgents/homebrew.mxcl.redis.plist
```

Once running, check that redis is doing so correctly:

```shell
$ redis-cli ping
```

If it replies `PONG`, you're all set!


## Set Up Python

We need to install a specific version of Python (v3.7, fow now?) that is separate from the version that comes pre-installed on the system. As above, you may do this [with Homebrew](https://docs.brew.sh/Homebrew-and-Python) -- `brew install python@3.7` -- but you'll probably find it easier to do this using [pyenv](https://github.com/pyenv/pyenv):

```shell
$ brew install pyenv
$ pyenv install 3.7.16
$ pyenv shell 3.7.16
```

Run `python3 --version` to confirm that the correct version is active.

You should always develop projects -- including colandr -- within isolated virtual environments. If you used pyenv above, consider using the accompanying pyenv-virtualenv package:

```shell
$ brew install pyenv-virtualenv
```

An alternative is to use the `virtualenv` package, installed with `pip`:

```shell
$ python3 -m pip3 install virtualenv
```

To create the project-specific env, you'll first need to create the project directory on disk. (See next section.)


## Set Up Colandr

Install `git`, for version control and access to the app's code:

```shell
$ brew install git
```

Now, clone the code from colandr's remote [repository on GitHub](https://github.com/datakind/permanent-colandr-back). Make a new local directory for the repo (if needed) and change your current working directory to it:

```shell
$ mkdir /path/to/project_dir
$ cd /path/to/project_dir
$ git clone https://github.com/datakind/permanent-colandr-back.git
```

This should create a `permanent-colandr-back` directory containing the app's source code. Now's a good time to create the project's virtual env. If you previously installed `pyenv-virtualenv`, do this:

```shell
$ cd permanent-colandr-back
$ pyenv virtualenv 3.7.16 <ENV_NAME>
$ pyenv local <ENV_NAME>
```

Or if you installed `virtualenv`, do this:

```shell
$ virtualenv <ENV_NAME>
$ source <ENV_NAME>/bin/activate
```

In either case, `ENV_NAME` should be descriptive, like "colandr-py37".

Into the activated virtual env, install the 3rd-party dependencies upon which the app relies:

```shell
$ pip3 install .
```

If you're planning to actively develop colandr, you'll probably want to do an editable install and include a few extra (dev-only) dependencies. To do that instead:

```shell
$ pip install -e .[dev]
```

The app's NLP functionality is built on the `spacy` package, which requires a manual download of model data. After installing it above, run the following commands:

```shell
$ python3 -m spacy download en_core_web_md
$ python3 -c "import spacy; spacy.load('en_core_web_md'); print('OK')"
```

The second command will print "OK" if the download was successful.

In some situations, you may have to add the repository directory to your `PYTHONPATH` environment variable by modifying the corresponding line (or adding a new line) in your `~/.profile` (or `~/.bashrc`, `~/.zshrc`, etc.) file:

```
export PYTHONPATH=/path/to/permanent-colandr-back/:$PYTHONPATH
```

Finally, create a few environment variables needed by the app to configure itself and send emails. `COLANDR_APP_DIR` is the location of the `permanent-colandr-back` directory on disk. `COLANDR_SECRET_KEY` acts like an app-wide password, so keep it secret, keep it safe, and keep it _strong_. `COLANDR_PASSWORD_SALT` is also like a password, used by the app when sending custom links in account registration confirmation emails. `COLANDR_MAIL_USERNAME` and `COLANDR_MAIL_PASSWORD` are the credentials for the email account that sends those emails.

```shell
$ export COLANDR_FLASK_CONFIG="default"
$ export COLANDR_APP_DIR="/path/to/permanent-colandr-back"
$ export COLANDR_SECRET_KEY="<YOUR_SECRET_KEY>"
$ export COLANDR_PASSWORD_SALT="<YOUR_PASSWORD_SALT>"
$ export COLANDR_MAIL_USERNAME="<AN_EMAIL_ADDRESS>"
$ export COLANDR_MAIL_PASSWORD="<THE_CORRESPONDING_PASSWORD>"
```

The `.env.example` file has these environment variables already written out. It may be convenient to copy this file, rename it to `.env`, set the desired variable values, then run `$ source .env`.
