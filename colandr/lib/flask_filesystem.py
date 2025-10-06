import typing as t

import flask
import fsspec


class FileSystem:
    config_prefix = "FILESYSTEM_"

    def __init__(
        self,
        *,
        app: t.Optional[flask.Flask] = None,
        protocol: t.Optional[str] = None,
        storage_options: t.Optional[dict] = None,
    ):
        self.protocol = protocol
        self.storage_options = storage_options or {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app: flask.Flask):
        config = app.config
        protocol = self.protocol or config.get(f"{self.config_prefix}PROTOCOL")
        storage_options = (
            config.get(f"{self.config_prefix}STORAGE_OPTIONS", {}).get(protocol, {})
            | self.storage_options
        )
        fs = fsspec.filesystem(protocol, **storage_options)

        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions["filesystem"] = fs
