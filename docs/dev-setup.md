# Dev Setup

These instructions generally assume that you're on a machine running macOS, though most if not all of this should work similarly on Linux. If you've already installed a given tool, there's no need to reinstall -- but you may want to update.


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

Lastly, use Homebrew to install [Docker](https://docs.docker.com), a tool for developing and running applications, and [git](https://git-scm.com), for version control and access to colandr's code:

```shell
$ brew cask install docker
$ brew install git
```

Confirm that Docker successfully installed by running `docker --version`; for a more extensive check, try `docker run hello-world`. You may also see the Docker icon in your system bar, which can be used to open the Docker for Desktop app.


## Set Up Colandr

Get a copy of the back-end code from colandr's [GitHub repository](https://github.com/datakind/permanent-colandr-back). Make a new local directory for the repo and change your current working directory to it, as needed:

```shell
$ mkdir /path/to/[YOUR-PROJECT-DIR]
$ cd /path/to/[YOUR-PROJECT-DIR]
$ git clone https://github.com/datakind/permanent-colandr-back.git
```

This creates a `permanent-colandr-back` directory containing the app's source code in `[YOUR-PROJECT-DIR]`.

Colandr needs a few environment variables to be set in order to configure itself and perform basic functionality, such as connecting to the database. These variables are declared and assigned to dummy values in the `.env.example` file found in the `permanent-colandr-back/` directory. Make a copy of the file in the same directory, name it `.env`, then fill in actual values for the included env vars. Note that this `.env` file is not version-controlled; it is environment-specific.


## Build and Run Colandr

Colandr's back-end system consists of multiple services defined and configured in `compose.yml`, including a PostgreSQL database, Flask API server, and Redis broker+worker. They are built and run via [Docker Compose](https://docs.docker.com/compose). Docker commands may be run from the `permanent-colandr-back/` directory.

To build and also run the application stack in "detached" mode (i.e. in the background), do

```shell
$ docker compose up --build --detach
```

Interactive API documentation is available in a web browser at "http://localhost:5001/docs". A development email server is available at "http://localhost:8025".

For application management instructions, go [here](./app-management.md)
