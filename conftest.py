from datetime import datetime


def pytest_configure(config):
    """Create a log file if log_file is not mentioned in *.ini file"""
    if not config.option.log_file:
        timestamp = datetime.strftime(datetime.now(), "%Y-%m-%d_%H-%M-%S")
        config.option.log_file = f"logs/pytest.{timestamp}.log"
