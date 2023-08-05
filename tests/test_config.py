from colandr.app import create_app


class TestConfig:
    def test_config_overrides(self):
        app = create_app({"TESTING": True})
        assert app.config["TESTING"] is True
