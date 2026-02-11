# for developers

Colandr's back-end system consists of multiple services defined and configured in `compose.yaml` and two `Dockerfile`s, including a PostgreSQL database, Flask API server, and Redis broker+worker.

## local setup

These instructions describe a one-time setup, started from scratch. They assume you're on a machine running macOS or Linux.

### install system tools

The colandr API is version-controlled using [git](https://git-scm.com) and run as a containerized application using [Docker](https://docs.docker.com); these tools must be installed on your system. If you already have a given tool, there's no need to reinstall -- but you may want to update.

Let's use [Homebrew](http://brew.sh), a handy package manager for macOS (or Linux), to install these tools. First, install Homebrew:

```shell
$ /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Be sure to follow any additional instructions provided by Homebrew, then make sure it's clean and up-to-date:

```shell
$ brew update && brew doctor
```

Now install git and Docker:

```shell
$ brew install git
$ brew install --cask docker
```

### get colandr

Get a local copy of the code from colandr's [GitHub repository](https://github.com/datakind/permanent-colandr-back):

```shell
$ mkdir /path/to/[YOUR-PROJECT-DIR]
$ cd /path/to/[YOUR-PROJECT-DIR]
$ git clone https://github.com/datakind/permanent-colandr-back.git
```

This creates a `permanent-colandr-back` directory containing the app's source code in `[YOUR-PROJECT-DIR]`.

Colandr needs a few environment variables to be set in order to configure itself and perform basic functionality, such as connecting to the database. These variables are declared and assigned to dummy values in the `.env.example` file found in the `permanent-colandr-back/` directory. Make a copy of the file in the same directory, name it `.env`, then fill in actual values for the included env vars. Note that this `.env` file is not version-controlled; it is environment-specific.

## app development

### build and run colandr

The colandr back-end system is built and run via [Docker Compose](https://docs.docker.com/compose). Note that for local development, you must specify the "dev" profile:

```shell
$ docker compose --profile dev up --build
```

Typically, you'll want to run the system in "detached" mode (i.e. in the background) by appending the `--detach` flag, or if making code changes, leverage Docker Compose's ["watch" functionality](https://docs.docker.com/compose/how-tos/file-watch/), by adding the `--watch` flag, so that containers are automatically reloaded/restarted as the underlying code changes.

Interactive API documentation is available in a web browser at "http://localhost:5001/docs". A development email server is available at "http://localhost:8025".

### check code

Various code checks are run automatically via GitHub Actions when opening pull requests, merging branches, and so on. These checks can also be run manually against your local application, either from the `colandr-api` container or from the host system by prepending `docker exec -it colandr-api` to the command.

Unit tests are implemented and invoked using [`pytest`](https://docs.pytest.org/en/7.1.x/reference/reference.html#command-line-flags):

```shell
$ docker exec -it colandr-api python -m pytest
```

Code is linted and formatted using [`ruff`](https://docs.astral.sh/ruff):

```shell
$ docker exec -it colandr-api bash
:/app# python -m ruff check colandr
:/app# python -m ruff format --check colandr
```

Types are checked using [`mypy`](https://mypy.readthedocs.io/en/stable):

```shell
$ docker exec -it colandr-api python -m mypy --install-types --non-interactive colandr
```

All tools' configurations live alongside package config in the root `pyproject.toml` file.

## app management

colandr's back-end Flask application includes a CLI with a few useful commands. Full details are available via the `--help` flag:

```shell
$ docker exec -it colandr-api flask --app "colandr.app.create_app()" --help
```

### initialize and modify the database

To create the app's database structure -- tables, etc. -- then populate it with data from scratch, run

```shell
$ docker exec -it colandr-api flask db-create
$ docker exec -it colandr-api flask db-seed --fpath /path/to/seed_data.json
```

Technically you can "db-create" whenever you like, but it only creates tables that don't already exist in the database; in contrast, running "db-seed" on an alread-populated database may run into duplicate data violations. To drop and then re-create all of the db's tables (to "reset" it), run

```shell
$ docker exec -it colandr-api flask db-reset
```

**Warning:** You will lose all data stored in the database! Be sure to only run this command in development or testing environments.

#### schema/data migrations

Database "revisions" are handled through [alembic](https://alembic.sqlalchemy.org) using the [`flask-migrate`](https://flask-migrate.readthedocs.io) package. Any time you modify db models -- add a column, remove an index, etc. -- run the following command to generate a migration script:

```shell
$ docker exec -it colandr-api flask db migrate -m [DESCRIPTION]
```

Review and edit the auto-generated file in the `permanent-colandr-back/migrations/versions` directory, since Alembic doesn't necessarily account for every change you can make. When ready, apply the migration to the database:

```shell
$ docker exec -it colandr-api flask db upgrade
```

Lastly, be sure to add and commit the migration file into version control.

Sometimes it's necessary to go back to an earlier revision. In that case:

```shell
$ docker exec -it colandr-api flask db downgrade <REVISION>
```

See the [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) for more details on and examples of its usage.

### add an admin

To add an admin user to the database -- a user with special powers in the app, and which can't be added via an API call -- run the following command:

```shell
$ docker exec -it colandr-api flask add_admin --name=[NAME] --email=[EMAIL] --password=[PASSWORD]
```

## Database Connection

### Create SSH Tunnel

```
ssh -i /path/to/colandr.pem \
  -L 5432:colandr-db.carpklcd5jnh.us-east-1.rds.amazonaws.com:5432 \
  ubuntu@34.232.91.109
```

### Connect via psql

```
psql -h localhost -p 5432 -U colandr
```

### Connect via GUI

Host: localhost
Port: 5432
SSL: Disabled

Credentials are stored in LastPass under:
Colandr – Production RDS Access
