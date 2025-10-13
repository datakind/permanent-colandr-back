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
        # HACK!
        if protocol == "gcs" and fs._endpoint is not None:
            self._gcs_create_bucket(app, fs.project, fs._endpoint)

    def _gcs_create_bucket(self, app: flask.Flask, project_id: str, api_endpoint: str):
        from google.auth.credentials import AnonymousCredentials
        from google.cloud import storage

        client = storage.Client(
            credentials=AnonymousCredentials(),
            project=project_id,
            client_options={"api_endpoint": api_endpoint},
        )
        bucket_name = app.config["FILESYSTEM_ROOT_DIR"]
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            app.logger.info("creating GCS bucket %s ...", bucket_name)
            client.create_bucket(bucket)
