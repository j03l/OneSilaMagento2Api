import glob
import logging
import os
import sys
import tempfile

# Add parent directory to path to import magento
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import magento
from magento.clients import Client
from magento.utils import LoggerUtils, MagentoLogger

DOMAIN = 'website.com'
USERNAME = 'username'
PASSWORD = 'password'

PKG_LOG_NAME = MagentoLogger.PACKAGE_LOG_NAME
PKG_LOG_FILE = PKG_LOG_NAME + '.log'
PKG_LOG_PATH = os.path.abspath(PKG_LOG_FILE)

PKG_HANDLER = MagentoLogger.get_package_handler()
PKG_HANDLER_NAME = '{}__{}__{}'.format(
    MagentoLogger.PREFIX, MagentoLogger.PACKAGE_LOG_NAME, "WARNING"
)


def test_file_logging_by_default():
    """Test that .log files are created by default"""
    # Create a temporary directory for clean testing
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Get initial .log files in directory
            initial_log_files = set(glob.glob('*.log'))
            assert len(initial_log_files) == 0, f"Expected clean directory, found: {initial_log_files}"

            # Test MagentoLogger directly with default behavior (should create files)
            test_logger = MagentoLogger(
                name="test-logger",
                stdout_level='INFO'
            )
            test_logger.info("Test message from direct logger")

            # Check for new .log files after direct logger test
            after_direct_log_files = set(glob.glob('*.log'))
            new_files_after_direct_log = after_direct_log_files - initial_log_files
            assert len(new_files_after_direct_log) == 1, f"Expected 1 log file created by default, got: {new_files_after_direct_log}"

            # Test that log_file property is set
            assert test_logger.log_file is not None, f"Expected log_file to be set by default, got: {test_logger.log_file}"
            assert test_logger.log_path is not None, f"Expected log_path to be set by default, got: {test_logger.log_path}"
            assert 'test-logger.log' in new_files_after_direct_log, "Expected test-logger.log to be created"

            print("✅ test_file_logging_by_default passed")

        finally:
            os.chdir(original_cwd)


def test_disable_file_logging():
    """Test that file logging can be disabled with disable_file_logging=True"""
    # Create a temporary directory for clean testing
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            # Get initial .log files in directory
            initial_log_files = set(glob.glob('*.log'))
            assert len(initial_log_files) == 0, f"Expected clean directory, found: {initial_log_files}"
            
            # Test MagentoLogger with disable_file_logging=True
            test_logger = MagentoLogger(
                name="test-logger",
                stdout_level='INFO',
                disable_file_logging=True
            )
            test_logger.info("Test message from logger with disabled file logging")
            
            # Check for new .log files after logger test
            after_log_files = set(glob.glob('*.log'))
            new_files = after_log_files - initial_log_files
            assert len(new_files) == 0, f"Expected no log files when disabled, got: {new_files}"
            
            # Test that log_file property is None
            assert test_logger.log_file is None, f"Expected log_file to be None when disabled, got: {test_logger.log_file}"
            assert test_logger.log_path is None, f"Expected log_path to be None when disabled, got: {test_logger.log_path}"
            
            print("✅ test_disable_file_logging passed")
            
        finally:
            os.chdir(original_cwd)


def test_file_logging_when_enabled():
    """Test that file logging works when explicitly enabled"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Test 1: Enable file logging via explicit log_file parameter
            test_logger = MagentoLogger(
                name="test-logger-explicit",
                log_file="test_explicit.log",
                stdout_level='INFO'
            )
            test_logger.info("Test message with explicit log file")

            # Check if log file was created
            explicit_log_files = set(glob.glob('*.log'))
            assert 'test_explicit.log' in explicit_log_files, "Explicit log file not created"
            assert os.path.exists('test_explicit.log'), "Log file doesn't exist"

            # Test 2: Enable file logging via MAGENTO_DEFAULT_LOG_DIR
            test_logs_dir = os.path.join(temp_dir, 'test_logs')
            os.environ['MAGENTO_DEFAULT_LOG_DIR'] = test_logs_dir

            test_logger2 = MagentoLogger(
                name="test-logger-env",
                log_file=None,  # None, but should create due to env var
                stdout_level='INFO'
            )
            test_logger2.info("Test message with environment log dir")

            # Check if log file was created in directory
            env_log_files = glob.glob(os.path.join(test_logs_dir, '*.log'))
            assert len(env_log_files) > 0, "No log files created in MAGENTO_DEFAULT_LOG_DIR"

            # Clean up env var
            del os.environ['MAGENTO_DEFAULT_LOG_DIR']

            print("✅ test_file_logging_when_enabled passed")

        finally:
            os.chdir(original_cwd)
            # Clean up env var if still set
            if 'MAGENTO_DEFAULT_LOG_DIR' in os.environ:
                del os.environ['MAGENTO_DEFAULT_LOG_DIR']


def test_client_disable_file_logging_parameter():
    """Test Client's disable_file_logging parameter"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Test 1: Client with default behavior (should create files)
            client1 = Client(
                domain='test.com',
                username='test',
                password='test',
                login=False
            )
            client1.logger.info("Test message from client with default file logging")

            after_client_default = set(glob.glob('*.log'))
            expected_file_pattern = 'test_com_test.log'
            assert any(expected_file_pattern in f for f in after_client_default), f"Expected file with pattern '{expected_file_pattern}' not found in: {after_client_default}"

            # Test 2: Client with disable_file_logging=True
            client2 = Client(
                domain='test2.com',
                username='test',
                password='test',
                login=False,
                disable_file_logging=True
            )
            client2.logger.info("Test message from client with disabled file logging")

            after_client_disabled = set(glob.glob('*.log'))
            new_files_disabled = after_client_disabled - after_client_default
            assert len(new_files_disabled) == 0, f"Unexpected log files with disable_file_logging=True: {new_files_disabled}"

            # Test 3: Explicit log_file parameter should override disable_file_logging
            client3 = Client(
                domain='test3.com',
                username='test',
                password='test',
                login=False,
                disable_file_logging=True,  # True, but explicit log_file should still work
                log_file='explicit_client.log'
            )
            client3.logger.info("Test message with explicit log file")

            after_explicit = set(glob.glob('*.log'))
            assert 'explicit_client.log' in after_explicit, "Explicit log file not created even with disable_file_logging=True"

            print("✅ test_client_disable_file_logging_parameter passed")

        finally:
            os.chdir(original_cwd)


def test_package_logger_creates_files_by_default():
    """Test that the package logger creates files by default"""
    # This test verifies that the package logger in magento/__init__.py
    # creates log files by default

    # The package logger should have log_file set and file handlers
    pkg_logger = magento.logger
    assert pkg_logger.log_file is not None, f"Package logger should have log_file set by default, got: {pkg_logger.log_file}"

    # Check that file handlers are present
    file_handlers = LoggerUtils.get_file_handlers(pkg_logger.logger)
    assert len(file_handlers) > 0, f"Package logger should have file handlers by default, found: {len(file_handlers)}"

    # Test logging creates files
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Create a new logger instance for testing in clean directory
            test_pkg_logger = MagentoLogger(
                name=MagentoLogger.PACKAGE_LOG_NAME,
                log_file=MagentoLogger.PACKAGE_LOG_NAME + '.log',
                stdout_level='WARNING'
            )
            test_pkg_logger.info("Test package log message")
            log_files = glob.glob('*.log')
            assert len(log_files) > 0, f"Package logger should create log files by default, found: {log_files}"

            print("✅ test_package_logger_creates_files_by_default passed")

        finally:
            os.chdir(original_cwd)


def test_package_logger():
    """Test package logger with file logging disabled by default"""
    pkg_logger = magento.logger
    pkg_logger.debug('Verifying package log file configuration...')
    pkg_log_files = LoggerUtils.get_log_files(pkg_logger.logger)

    assert pkg_logger.name == PKG_LOG_NAME
    assert pkg_logger.log_file is not None  # Should be set by default
    assert len(pkg_log_files) > 0  # File logging by default

    # File handlers should exist
    file_handlers = LoggerUtils.get_file_handlers(pkg_logger.logger)
    assert len(file_handlers) > 0, f"Expected file handlers by default, found: {len(file_handlers)}"

    pkg_logger.debug('Package logger has file logging by default')

    pkg_logger.debug('Verifying Package logger stdout configuration...')
    pkg_stream_handlers = LoggerUtils.get_stream_handlers(pkg_logger.logger)
    assert len(pkg_stream_handlers) == 1
    assert pkg_stream_handlers[0].level == logging.WARNING
    assert pkg_stream_handlers[0].name == PKG_HANDLER_NAME
    pkg_logger.debug('Package StreamHandler is configured correctly')


def test_package_logger_with_env_var():
    """Test package logger with MAGENTO_DEFAULT_LOG_DIR environment variable"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        log_dir = os.path.join(temp_dir, 'logs')
        try:
            os.chdir(temp_dir)
            os.environ['MAGENTO_DEFAULT_LOG_DIR'] = log_dir

            # Re-import to test with environment variable
            import importlib
            importlib.reload(magento.utils)
            importlib.reload(magento)

            pkg_logger = magento.logger

            # Now the package logger should have file logging enabled
            assert pkg_logger.log_file is not None, "Package logger should have file logging when MAGENTO_DEFAULT_LOG_DIR is set"
            assert log_dir in pkg_logger.log_file, f"Log file should be in {log_dir}, got: {pkg_logger.log_file}"

            # Test that logging creates the file
            pkg_logger.info("Test message with env var")
            assert os.path.exists(pkg_logger.log_file), f"Log file should exist at: {pkg_logger.log_file}"

            pkg_logger.debug('Package logger with MAGENTO_DEFAULT_LOG_DIR works correctly')

        finally:
            os.chdir(original_cwd)
            if 'MAGENTO_DEFAULT_LOG_DIR' in os.environ:
                del os.environ['MAGENTO_DEFAULT_LOG_DIR']
            # Re-import to reset to default state
            import importlib
            importlib.reload(magento.utils)
            importlib.reload(magento)


def test_client_logger_access(client: Client):
    """Test to make sure the Client attribute and method return the same object

    NOTE:
    client.logger -> MagentoLogger
    client.logger.logger -> logging.Logger
    """
    logger.debug('Verifying correct logger is returned from logger attribute and get_logger() method...')
    attr = client.logger.logger
    # Use the same disable_file_logging setting as the original client logger
    meth = client.get_logger(disable_file_logging=getattr(client.logger, 'disable_file_logging', False)).logger
    assert attr == meth
    logger.debug('Logger access is correct')
    return True


def test_client_logger_file_handlers(client: Client, log_file: str = None, expect_file_logging: bool = True):
    """Test client file handler configuration"""
    logger.debug('Verifying client log file configuration...')
    client_logger = client.logger
    client_name = MagentoLogger.CLIENT_LOG_NAME.format(
        domain=client.BASE_URL.split('://')[-1].split('/')[0].replace('.', '_'),
        username=client.USER_CREDENTIALS['username']
    )

    assert client_logger.name == client_name

    if expect_file_logging:
        # File logging is expected
        client_log_file = log_file if log_file else f'{client_name}.log'
        client_log_path = os.path.abspath(client_log_file)

        assert client_logger.log_file == client_log_file
        assert client_logger.log_path == client_log_path
        assert os.path.exists(client_logger.log_path)
        assert client_logger.log_path in client_logger.log_files

        logger.debug('Client log files are configured correctly')

        # Note: Package handler behavior changed - it's None by default now
        pkg_handler = MagentoLogger.get_package_handler()
        if pkg_handler is not None:
            assert pkg_handler in client_logger.handlers
            assert pkg_handler.baseFilename in client_logger.log_files
        else:
            logger.debug('Package handler is None (no file logging by default)')
    else:
        # No file logging expected
        assert client_logger.log_file is None, f"Expected no file logging, but log_file is: {client_logger.log_file}"
        assert client_logger.log_path is None, f"Expected no file logging, but log_path is: {client_logger.log_path}"

        file_handlers = LoggerUtils.get_file_handlers(client_logger.logger)
        assert len(file_handlers) == 0, f"Expected no file handlers, found: {len(file_handlers)}"

        logger.debug('Client has no file logging (correct)')

    logger.debug('Log file configuration is correct')
    return True


def test_client_logger_stream_handlers(client: Client):
    logger.debug('Verifying client stdout configuration...')
    client_logger = client.logger
    client_name = MagentoLogger.CLIENT_LOG_NAME.format(
        domain=client.BASE_URL.split('://')[-1].split('/')[0].replace('.', '_'),
        username=client.USER_CREDENTIALS['username']
    )
    client_stream_handlers = LoggerUtils.get_stream_handlers(client_logger)

    assert len(client_stream_handlers) == 1  # Should just be Client handler

    stream_handler_name = MagentoLogger.HANDLER_NAME.format(name=client_name, stdout_level="INFO")  # Default level
    stream_handler = client_stream_handlers[0]

    assert stream_handler.name == stream_handler_name
    assert stream_handler.level == logging.INFO

    logger.debug('Default stdout configuration is correct')
    logger.debug('Reconfiguring logger to use DEBUG stdout log level...')

    client_logger.setup_logger(stdout_level='DEBUG')
    client_stream_handlers = LoggerUtils.get_stream_handlers(client_logger)
    stream_handler_name = MagentoLogger.HANDLER_NAME.format(name=client_name, stdout_level="DEBUG")

    assert len(client_stream_handlers) == 1
    assert client_stream_handlers[0].level == logging.DEBUG
    assert client_stream_handlers[0].name == stream_handler_name

    logger.debug('Client logger level changed to DEBUG. Logging from Client...')
    client_logger.debug('If you can see this, log level was changed successfully')
    logger.debug("Changing client logger level back to INFO")

    client_logger.setup_logger(stdout_level="INFO")
    client_stream_handlers = LoggerUtils.get_stream_handlers(client_logger)
    stream_handler_name = stream_handler_name.replace("DEBUG", "INFO")  # From above

    assert len(client_stream_handlers) == 1
    assert client_stream_handlers[0].level == logging.INFO
    assert client_stream_handlers[0].name == stream_handler_name

    logger.debug('stdout log configuration is correct')
    return True


def test_log_file_change(client: Client):
    logger.debug('Verifying log file changes are accounted for...')
    client_logger = client.logger
    client_log_file_og = client_logger.log_file
    client_log_path_og = client_logger.log_path

    logger.debug(f'Current Log File: {client_log_file_og}')

    client_log_file_new = 'test_' + client_log_file_og
    client_logger.log_file = client_log_file_new

    logger.debug(f'Changed log file for client to {client_logger.log_file}')
    logger.debug('Setting up logger...')

    current_level = LoggerUtils.get_stream_handlers(client_logger)[0].name.split("__")[-1]  # StreamHandler.name = {}__{}__{stdout_level}
    client_logger.setup_logger(stdout_level=current_level)

    logger.debug(f'New logger set up. Should still be {current_level} for stdout, and writing only to the new log file')
    logger.debug('Verfying stdout configuration...')

    client_stream_handlers = LoggerUtils.get_stream_handlers(client_logger)

    assert len(client_stream_handlers) == 1
    assert client_stream_handlers[0].level == logging.getLevelName(current_level)

    logger.debug('Stdout configuration as expected.')
    logger.debug('Checking log file configuration...')

    if test_client_logger_file_handlers(client, client_log_file_new):
        logger.debug('New FileHandler set up correctly')

    logger.debug('Making sure previous FileHandler is fully removed...')

    client_log_files = LoggerUtils.get_log_files(client_logger)
    magento_handlers = MagentoLogger.get_magento_handlers(client_logger)

    assert client_log_path_og not in client_log_files  # The previous log file
    assert LoggerUtils.get_handler_by_log_file(client_logger, client_log_file_og) is None  # Handler should be removed too
    # Count should be 2 (client file handler + package handler) since package handler is enabled by default
    file_handler_count = len([handler for handler in magento_handlers if isinstance(handler, logging.FileHandler)])
    assert file_handler_count == 2, f"Expected 2 file handlers (client + package), found {file_handler_count}"
    logger.debug('Previous FileHandler is fully removed')


def test_for_requests_logger(client: Client, expect_file_logging: bool = True):
    """Test requests logger integration"""
    import requests

    requests_logger = requests.urllib3.connectionpool.log
    requests_log_files = LoggerUtils.get_log_files(requests_logger)

    if expect_file_logging:
        # When file logging is enabled, requests should log to files
        if client.logger.log_path:
            assert client.logger.log_path in requests_log_files, "Client log file should be in requests logger"

        pkg_handler = MagentoLogger.get_package_handler()
        if pkg_handler:
            assert pkg_handler.baseFilename in requests_log_files, "Package log file should be in requests logger"

        logger.debug('The requests package logger is writing to the appropriate log files')
    else:
        # When file logging is disabled, requests logger might not have files
        logger.debug(f'Requests logger has {len(requests_log_files)} log files (file logging disabled)')


if __name__ == '__main__':
    # Test default behavior (files by default) and disable functionality
    print("Testing default behavior (files by default) and disable functionality...")
    test_package_logger_creates_files_by_default()
    test_file_logging_by_default()
    test_disable_file_logging()
    test_file_logging_when_enabled()
    test_client_disable_file_logging_parameter()
    print("All logging tests passed! ✅\n")

    # Create a logger with explicit file logging for the remaining tests
    logger = MagentoLogger(
        name='logger_test',
        log_file='logger_test.log',
        stdout_level='DEBUG'
    )

    logger.debug('Beginning additional logger tests (with file logging enabled)...')

    # Test package logger behavior
    test_package_logger()
    test_package_logger_with_env_var()

    logger.debug('Switching to Client logger for remaining tests...')

    # Create client with file logging enabled
    client = Client(
        domain=DOMAIN,
        username=USERNAME,
        password=PASSWORD,
        login=False
        # File logging is enabled by default
    )

    logger.debug('Testing client logger functionality...')

    test_client_logger_access(client)
    test_client_logger_file_handlers(client, expect_file_logging=True)
    test_client_logger_stream_handlers(client)
    test_log_file_change(client)
    test_for_requests_logger(client, expect_file_logging=True)

    # Also test a client without file logging (in a clean environment)
    logger.debug('Testing client without file logging...')

    # Use a different domain/username to get a fresh logger
    client_no_file = Client(
        domain='test-no-file.com',
        username='test-user',
        password='test-pass',
        login=False,
        disable_file_logging=True  # Disable file logging for this client
    )

    test_client_logger_access(client_no_file)
    test_client_logger_file_handlers(client_no_file, expect_file_logging=False)
    test_client_logger_stream_handlers(client_no_file)
    test_for_requests_logger(client_no_file, expect_file_logging=False)

    logger.debug('All tests passed')
    print("All logger tests completed successfully! ✅")
    sys.exit(0)
