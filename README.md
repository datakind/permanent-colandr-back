# `colandr`

Back-end code for [colandr](https://www.colandrapp.com), an ML-assisted online application for conducting systematic reviews and syntheses of text-based evidence.

## local dev setup

Minimal setup instructions, from the beginning, for devs who don't need checks or explanations:

1. Install Xcode: `xcode-select --install`
1. Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
1. Install Docker and git: `brew cask install docker && brew install git`
1. Clone copy of colandr repo: `git clone https://github.com/datakind/permanent-colandr-back.git`
1. Build and spin up application services: `cd permanent-colandr-back && docker compose up --build --detach`

For more details, see the instructions [here](docs/dev-setup.md).

## app management

(todo: basics here)

For more details, see the instructions [here](docs/app-management.md)
