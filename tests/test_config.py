from colandr.app import create_app_v1


class TestConfig:
    def test_config_overrides(self):
        app = create_app_v1({"TESTING": True})
        assert app.config["TESTING"] is True
