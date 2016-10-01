## App and DB Management

Most app+db management tasks are handled by the `manage.py` script, found at the top level of the `conservation-intl` directory where the repository was cloned on disk. To get help on available commands, run the following:

```
$ python3 manage.py --help
```

And to get help for a specific command:

```
$ python3 manage.py <command> --help
```

For all commands, you can specify the particular app configuration to act upon. This is particularly important if different configs are associated with different databases! Running the `help` command above also shows the available configurations; if desired, specify the config name _before_ the command name, like so:

```
$ python3 manage.py --config=<config_name> <command>
```

## Initialize, Migrate, and Upgrade the Database

If the `conservation-intl/migrations` directory does not exist (**Note:** It should!), issue the following command to initialize the migrations directory and its contents:

```
$ python3 manage.py db init
```

If the database models have changed _or_ a current migration script does not exist in the `conservation-intl/migrations/versions` directory (**Note:** It should!), issue the following command to generate a migration script using Alembic:

```
$ python3 manage.py db migrate
```

If you generated a new migration script, it must be reviewed and edited because Alembic doesn't necessarily detect every change you made to the models. There's also a known bug when dealing with `postgresql` arrays (see [here](https://bitbucket.org/zzzeek/alembic/issues/85/using-postgresqlarray-unicode-breaks)) that directly affects us. Open the newly-created `conservation-intl/migrations/versions/<version>.py` module, then do a find-and-replace to convert every instance of "`ARRAY(Unicode`" with "`ARRAY(sa.Unicode`". If you skip this, the next command will throw an exception pointing you to the problematic line, so we might as well be proactive.

Be sure to add the migration script (and the whole `migrations` directory, for that matter) to version control, if it's not already in there!

Finally, _in all cases_, apply the migration to the database:

```
$ python3 manage.py db upgrade
```

Any time you change the database models, run the `db migrate` and `db upgrade` commands again, and `git commit && git push` the new version to the remote git repo. If you just need to sync the database in a system, update the `conservation-intl/migrations` directory from version control via `git pull` and run the `db upgrade` command only.


## Reset and Re-populate the Database

In order to "reset" the database by dropping and then re-creating all of its tables, run the following command:

```
$ python3 manage.py reset_db
```

**Note:** This is permanent! So be very sure that this is what you want. (Don't worry, there's a prompt to confirm.)

An administrator is automatically added to the database as its first user; if that behavior is unwanted, specify the `no_admin` flag:

```
$ python3 manage.py reset_db --no_admin
```

To re-populate the database from scratch (i.e. after running the above command), a separate script is used — for now. Call it like so:

```
$ python3 repopulate_db.py
```

As above, use `--help` to see run options, and specify an app configuration with the `--config` flag.

## Run the App

To order to run the app, just do this:

```
$ python3 migrate.py runserver
```
