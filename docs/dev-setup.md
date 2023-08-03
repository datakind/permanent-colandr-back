# Dev Setup

Minimal setup instructions, for devs who don't need checks or explanations:

1. Install Xcode: `xcode-select --install`
1. Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
1. Install Docker: `brew cask install docker`
1. Clone copy of colandr repo: `brew install git && git clone https://github.com/datakind/permanent-colandr-back.git`
1. Build and spin up application services: `docker compose up --build --detach`

As for the rest of us... read on!

These instructions generally assume that you're on a machine running macOS, though most of them should work similarly on Linux. If you've already installed a given tool, there's no need to reinstall -- but you may want to update it.


## Install System Tools

Install Xcode's command line tools, which includes many low-level tools that others rely upon. From a terminal/shell prompt, run:

```shell
$ xcode-select --install
```

Install [Homebrew](http://brew.sh), which is a handy package manager for macOS (or Linux):

```shell
$ /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Be sure to follow any additional instructions given by Homebrew. In any case, you should probably update Homebrew and give it a check-up:

```shell
$ brew update
$ brew doctor
```

Lastly, use Homebrew to install [Docker](https://docs.docker.com), a tool for developing and running applications. This should install it in both command line and native application form:

```shell
$ brew cask install docker
```

Confirm that Docker successfully installed by running `docker --version`; for a more extensive check, try `docker run hello-world`. You may also see the Docker icon in your system bar, which may be used to open the Docker for Desktop app.


## Set Up Colandr

Install `git`, for version control and access to the app's code:

```shell
$ brew install git
```

Get a copy of the back-end code from colandr's [GitHub repository](https://github.com/datakind/permanent-colandr-back). Make a new local directory for the repo and change your current working directory to it, as needed:

```shell
$ mkdir /path/to/[YOUR-PROJECT-DIR]
$ cd /path/to/[YOUR-PROJECT-DIR]
$ git clone https://github.com/datakind/permanent-colandr-back.git
```

This creates a `permanent-colandr-back` directory containing the app's source code in `[YOUR-PROJECT-DIR]`.

Colandr needs a few environment variables to be set in order to configure itself and perform basic functionality, such as connecting to the database. These variables are declared and assigned to dummy values in the `.env.example` file found in the `permanent-colandr-back/` directory. Make a copy of the file in the same directory, name it `.env`, then fill in actual values for the included env vars. Note that this `.env` file is not version-controlled; it is environment-specific.


## Build and Run Colandr

Colandr's back-end system consists of multiple services defined and configured in `compose.yml`, including a PostgreSQL database, Flask API server, and Redis broker+worker. They are built and run via [Docker Compose](https://docs.docker.com/compose). Docker commands may be run from the `permanent-colandr-back/` directory. To trigger a build, run

```shell
$ docker compose build
```

To build and also run the application services in "detached" mode (i.e. in the background), do

```shell
$ docker compose up --build --detach
```

The Flask application includes a CLI with a few useful commands that may be invoked directly from inside the `colandr-api` container or via docker from outside the container. To create the app's database structure (tables, etc.) from scratch, run

```shell
$ docker exec -it colandr-api flask create-db
```

Technically you can run this whenever you like, but it only creates tables that don't already exist in the database. To manually _reset_ an existing database by dropping and then re-creating all of its tables, do

```shell
$ docker exec -it colandr-api flask reset-db
```

**Note:** You will lose all data stored in the database! So be sure to only run this command in development or testing environments.

Information about all available commands and sub-commands can be had via the `--help` flag:

```shell
$ docker exec -it colandr-api flask --help
```

To run unit tests on your host machine against running application services, do this:

```shell
$ pytest -v tests
```
