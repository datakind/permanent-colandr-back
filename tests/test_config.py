from colandr.app import create_app


class TestConfig:
    def test_prod_config(self):
        app = create_app("prod")
        assert app.config['DEBUG'] is False
        assert app.config['TESTING'] is False

    def test_dev_config(self):
        app = create_app("dev")
        assert app.config['TESTING'] is False

    def test_test_config(self):
        app = create_app("test")
        assert app.config['TESTING'] is True
