# App Management

The colandr back-end Flask application includes a CLI with a few useful commands that may be invoked directly from inside the `colandr-api` container or via docker from outside the container (by prepending `docker exec -it colandr-api`).

Information about all available commands and sub-commands can be had via the `--help` flag:

```shell
$ docker exec -it colandr-api flask --help
```

## Initialize and Migrate the Database

To create the app's database structure -- tables, etc. -- then populate it with data from scratch, run

```shell
$ docker exec -it colandr-api flask db-create
$ docker exec -it colandr-api flask db-seed --fpath /path/to/seed_data.json
```

Technically you can "db-create" whenever you like, but it only creates tables that don't already exist in the database; in contrast, running "db-seed" on an alread-populated database may run into duplicate data violations. To manually _reset_ an existing database by dropping and then re-creating all of its tables, do

```shell
$ docker exec -it colandr-api flask db-reset
```

**Warning:** You will lose all data stored in the database! So be sure to only run this command in development or testing environments.

Database "revisions" are handled through [alembic](https://alembic.sqlalchemy.org/en/latest) using the [`flask-migrate`](https://flask-migrate.readthedocs.io) package. Any time you modify db models -- add a column, remove an index, etc. -- run the following command to generate a migration script:

```shell
$ docker exec -it colandr-api flask db migrate -m [DESCRIPTION]
```

Review and edit the auto-generated file in the `permanent-colandr-back/migrations/versions` directory, since Alembic doesn't necessarily account for every change you can make. When ready, apply the migration to the database:

```shell
$ docker exec -it colandr-api flask db upgrade
```

Lastly, be sure to add and commit the file into version control!


## Unit Testing

Unit tests are implemented and invoked using `pytest`. The test suite is run on the `colandr-api` container, like so:

```shell
$ docker exec -it colandr-api python -m pytest [OPTIONS]
```


---
(old stuff)

## App and DB Management

Most app+db management tasks are handled by the `manage.py` script, found at the top level of the `permanent-colandr-back` directory where the repository was cloned on disk. To get help on available commands, run the following:

```
$ python3 manage.py --help
```

And to get help for a specific command:

```
$ python3 manage.py <command> --help
```

For all commands, you can specify the particular app configuration to act upon. This is particularly important if different configs are associated with different databases! This command line option will override the value given by the environment variable 'COLANDR_FLASK_CONFIG' or, lacking that, just 'default'.

Running the `help` command above also shows the available configurations; if desired, specify the config name _before_ the command name, like so:

```
$ python3 manage.py --config=<config_name> <command>
```

## Initialize, Migrate, and Upgrade the Database

If the `permanent-colandr-back/migrations` directory does not exist (**Note:** It should!), issue the following command to initialize the migrations directory and its contents:

```
$ python3 manage.py db init
```

If the database models have changed _or_ a current migration script does not exist in the `permanent-colandr-back/migrations/versions` directory (**Note:** It should!), issue the following command to generate a migration script using Alembic:

```
$ python3 manage.py db migrate
```

If you generated a new migration script, it must be reviewed and edited because Alembic doesn't necessarily detect every change you made to the models. There's also a known bug when dealing with `postgresql` arrays (see [here](https://bitbucket.org/zzzeek/alembic/issues/85/using-postgresqlarray-unicode-breaks)) that directly affects us. Open the newly-created `permanent-colandr-back/migrations/versions/<version>.py` module, then do a find-and-replace to convert every instance of "`ARRAY(Unicode`" with "`ARRAY(sa.Unicode`". If you skip this, the next command will throw an exception pointing you to the problematic line, so we might as well be proactive.

Be sure to add the migration script (and the whole `migrations` directory, for that matter) to version control, if it's not already in there!

Finally, _in all cases_, apply the migration to the database:

```
$ python3 manage.py db upgrade
```

Any time you change the database models, run the `db migrate` and `db upgrade` commands again, and `git commit && git push` the new version to the remote git repo. If you just need to sync the database in a system, update the `permanent-colandr-back/migrations` directory from version control via `git pull` and run the `db upgrade` command only.


## Run the App

To order to run the app, you'll need to have both Postgres and Redis running as services on your machine; refer to the `dev-env-setup` document for the start/stop commands.

In order to send registration emails, de-duplicate citations, or suggest keyterms, you'll need to run the celery worker that listens for asynchronous tasks sent by the flask app. From within the `permanent-colandr-back` directory, just do this:

```
$ celery worker --app=celery_worker.celery
```

For day-to-day development, it's fine to run the app using flask's regular server, which serves only one request at a time:

```
$ python3 manage.py runserver
```

In production, however, we'll run our app using a more scalable server: `gunicorn`, which handles multiple requests at once and complicated things like threading. The gunicorn server's configuration is specified in `gunicorn_config.py`; for a full explanation of the options, check out [the docs](http://docs.gunicorn.org/en/stable/index.html). To run the app via gunicorn, just do this:

```
$ gunicorn --config=gunicorn_config.py gunicorn_runserver:app --log-file=colandr.log
```


## Add an Administrator

To add an admin user to the database — a user with special powers in the app, and which can't be added via an API call — run the following command:

```
$ python3 manage.py add_admin --name=[NAME] --email=[EMAIL] --password=[PASSWORD]
```

**Note:** This used to be done automatically in the ``reset`` command. See below.


## Reset and Re-populate the Database

In order to "reset" the database by dropping and then re-creating all of its tables, clearing out files uploaded to disk, and adding an administrator user, run the following command:

```
$ python3 manage.py reset
```

**Warning:** This is permanent! So be very sure that this is what you want. (Don't worry, there's a prompt to confirm.)

To re-populate the database from scratch (i.e. after running the above command), a separate script is used — for now. It actually calls the APIs used in the app, so you'll need both the flask app and celery worker running in other terminals (see above). Then, run the script:

```
$ python3 repopulate_db.py
```

As above, use `--help` to see run options, and specify an app configuration with the `--config` flag. **Note:** This script expects a few files to exist on disk:

- `/path/to/colandr_data/citations/ci-full-collection-group1.ris`
- `/path/to/colandr_data/citations/ci-full-collection-group2.ris`
- `/path/to/colandr_data/dedupe/dedupe_citations_settings`

If you don't have these files, the script will not finish successfully. _Ask and ye shall receive_.
