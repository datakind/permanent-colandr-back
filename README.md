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

For more details, see the instructions [here](docs/app-management.md)
