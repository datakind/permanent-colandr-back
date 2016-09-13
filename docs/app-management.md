## Initialize, Migrate, and Upgrade the Database

Navigate to the `conservation-intl` directory (the cloned repo on disk). If the `conservation-intl/migrations` directory does not exist (**Note:** It should!), issue the following command to initialize the migrations directory and its contents:

```
$ python3 manage.py db init
```

If the database models have changed _or_ a current migration script does not exist in the `conservation-intl/migrations/versions` directory (**Note:** It probably should!), issue the following command to generate a migration script using Alembic:

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

In order to "reset" the database by dropping and then re-creating all of its tables (**Note:** This is permanent! So be very sure that this is what you want...), run the following script:

```
$ python3 reset_db.py
```

You can specify particular app configurations, if these are associated with separate databases. Options can be seen by calling the script's "help":

```
$ python3 reset_db.py --help
$ python3 reset_db.py --config=<CONFIG_NAME>
```

Check out the `api-tests.ipynb` notebook in the `conservation-intl/notebooks` directory for an example of how to populate and otherwise interact with the database via the REST API. **TODO:** Add more details here.


## Run the App

To order to run the app, navigate to the repo and run the following script:

```
$ python3 run.py
```

As above, different app configurations (and perhaps database) can be run by specifying the `config` option:

```
$ python3 run.py --config=<CONFIG_NAME>
```
