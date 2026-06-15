# `colandr`

Back-end code for [colandr](https://www.colandrapp.com), an ML-assisted online application for conducting systematic reviews and syntheses of text-based evidence.

## local dev setup

Minimal setup instructions, from the beginning, for devs who don't need checks or explanations:

1. Install Xcode: `xcode-select --install`
2. Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
3. Install Docker and git: `brew install --cask docker && brew install git`
4. Clone copy of colandr repo: `git clone https://github.com/datakind/permanent-colandr-back.git`
5. Build and spin up application services: `cd permanent-colandr-back && docker compose --profile dev up --build --watch`*

*Note: `--profile dev` manages the "colandr-email" image build. When this is excluded in production, the email image will not build. It's expected that an external email API service will be used in its place.

For more details, see the instructions [here](docs/dev-setup.md).

## app management

(todo: basics here)

For more details, see the instructions [here](docs/app-management.md).

## Git worktree (prod + `develop` on one machine)

A normal repo has **one** working tree: one directory, one checked-out branch. **`git worktree add`** adds **another** directory that shares the same `.git` object database but can sit on a **different branch** (e.g. `develop`) while your main clone stays on `main`.

Typical flow from the **production** clone (paths are examples — use your own):

```bash
cd /path/to/permanent-colandr-back
git fetch origin
git worktree add ../permanent-colandr-back-develop develop
```

You now have two directories: the original checkout on your **production** branch, the worktree on **`develop`**. Both share the same Git objects; commits in one are visible to the other after `git fetch`.

For `compose.prod.yaml`, set in the project **`.env`** (Compose reads it for variable substitution):

```bash
COLANDR_DATA_DIR=/absolute/path/to/colandr_data
COLANDR_DEVELOP_BUILD_CONTEXT=/absolute/path/to/permanent-colandr-back-develop
```

Copy `.env.example` to **`.env` inside the worktree** and set develop DB, Celery URLs, etc. (Compose loads that file as `${COLANDR_DEVELOP_BUILD_CONTEXT}/.env` for `api-develop`; prod `api` / `worker` still use the **main** clone’s `.env` only.)

Then build/run with **`docker compose -f compose.prod.yaml --profile develop …`** from the main clone (or rely on **`COMPOSE_PROFILES=develop`** from `deployment/systemd/colandr-api.service` on boot). Remove the worktree later with `git worktree remove ../permanent-colandr-back-develop` (from the main repo, after stopping containers that use that path).
