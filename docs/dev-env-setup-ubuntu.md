## Set Up System Tools

We can set up most of what we need using apt-get. First update apt-get to pull from latest sources:

```
$ sudo apt-get update
```

Also install `git`, for version control and (later) access to the app's code:

```
$ sudo apt-get install git
```


## Set Up PostgreSQL

If you want to use a postgres database on another server (like RDS) you can skip this step, however you will need to install 
postgres libraries for python to read from it:

```
$ sudo apt-get install libpq-dev
```

Install with apt-get, you need to add a new source first:

```
$ sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -cs`-pgdg main" >> /etc/apt/sources.list.d/pgdg.list'
$ wget -q https://www.postgresql.org/media/keys/ACCC4CF8.asc -O - | sudo apt-key add -
```

And then install postgres:

```
$ sudo apt-get update
$ sudo apt-get install postgresql postgresql-contrib
$ sudo apt-get install python-psycopg2
$ sudo apt-get install libpq-dev
```

Postgres installation automatically created a database superuser account with the login of 'postgres'. Let's create a dedicated user named `colandr_app` for connecting to and owning the app's database:

```
$ sudo su - postgres
$ createuser --echo --pwprompt --superuser --createdb colandr_app
```

You'll be prompted to create a password — be sure to remember it or save it somewhere!

Postgres also automatically created a database named `postgres` that may be used to log info for administrative tasks such as creating a user. Let's create a new database for this project (the default port for postgres is usually 5432):

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

Redis is an in-memory data structure store, commonly used as a database, cache, and (as in the case of `colandr`) a message broker. Install it with apt-get:

Now, let's install Redis from the Ubuntu repository. Before installing Redis, let's update the system to latest update first.

```
$ sudo apt-get update $ sudo apt-get upgrade
```

After updating the system, it's time to install Redis from the repository.

```
$ sudo apt-get -y install redis-server
``` 
By default, redis-server is started after installation. You can check using the service command :

```
$ sudo service redis-server status redis-server is running
```

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
$ export COLANDR_APP_DIR="/path/to/conservation-intl"
$ export COLANDR_SECRET_KEY="<YOUR_SECRET_KEY>"
$ export COLANDR_PASSWORD_SALT="<YOUR_PASSWORD_SALT>"
$ export COLANDR_MAIL_USERNAME="<AN_EMAIL_ADDRESS>"
$ export COLANDR_MAIL_PASSWORD="<THE_CORRESPONDING_PASSWORD>"
```


## Set Up Python 3

For a fuller guide to everything below, check out [The Hitchhiker's Guide to Python](http://docs.python-guide.org/en/latest/).

Python 3 should already be installed, but you will need pip3:

```
$ sudo apt-get install python3-pip
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
$ sudo apt-get build-dep python3-matplotlib
$ sudo apt-get install python3-numpy
$ sudo apt-get install python3-scipy
$ sudo apt-get install python3-matplotlib
$ pip3 install cython
$ pip3 install semver
$ sudo apt-get install libatlas-dev
$ sudo apt-get install libopenblas-dev
$ pip3 install -r requirements.txt
$ sudo pip3 install werkzeug
$ sudo pip3 install jinja2
$ sudo pip3 install click
$ sudo pip3 install kombu
$ sudo pip3 install billiard
$ sudo pip3 install aniso8601
$ sudo pip3 install smart_open
$ sudo pip3 install toolz
$ sudo pip3 install cycler
$ sudo pip3 uninstall highered
$ sudo pip3 install highered
$ sudo pip3 install flask_restful_swagger
$ sudo pip3 install werkzeug
$ sudo pip3 install jinja2
$ sudo pip3 install click
$ sudo pip3 install kombu
$ sudo pip3 install billiard
$ sudo pip3 install aniso8601
$ sudo pip3 install smart_open
$ sudo pip3 install toolz
$ sudo pip3 install cycler
$ sudo pip3 uninstall highered
$ sudo pip3 install highered
$ sudo pip3 install flask_restful_swagger
```

The app's NLP is built on the `spacy` package, which requires a manual download of model data. After installing it above, run the following commands:

```
$ python3 -m spacy.en.download all --force
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

## To install the scala tools that perform some NLP and pdf extraction tasks:

If you need to install java:

```
$ sudo apt-add-repository ppa:webupd8team/java
$ sudo apt-get update
$ sudo apt-get install oracle-java8-installer
$ sudo apt-get install maven
```

Go into the pdfestrian directory and install the library:
```
$ cd pdfestrian
$ mvn package
```