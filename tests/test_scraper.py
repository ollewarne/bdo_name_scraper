import pytest
from unittest.mock import patch, MagicMock

from scraper import validate_proxy, load_proxies, check_name, PROXY_FAILED


def test_validate_proxy_success():
    with patch("scraper.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        result = validate_proxy("1.2.3.4:8080")
        assert result == {"http": "http://1.2.3.4:8080", "https": "http://1.2.3.4:8080"}


def test_validated_proxy_failure():
    with patch("scraper.requests.get") as mock_get:
        mock_get.side_effect = Exception("connection failed")
        result = validate_proxy("1.2.3.4:8080")
        assert result is None


def test_load_proxies_filter_empty_lines():
    with patch("scraper.requests.get") as mock_get:
        mock_get.return_value.text = "\nthis\nis\na\n\ntest\n"
        result = load_proxies("http://test.test")
        assert result == ["this", "is", "a", "test"]


def test_check_name_available():
    with patch("scraper.requests.get") as mock_get:
        with patch("scraper.time.sleep") as mock_sleep:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "<li class='no_result'></li>"
            proxy = {
                "http": "http://999.888.777.666:4444",
                "https": "http://999.888.777.666:4444",
            }
            result = check_name("TestName", "NA", 1, proxy)
            assert result


def test_check_name_taken():
    with patch("scraper.requests.get") as mock_get:
        with patch("scraper.time.sleep") as mock_sleep:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "<li>taken</li>"
            proxy = {
                "http": "http://999.888.777.666:4444",
                "https": "http://999.888.777.666:4444",
            }
            result = check_name("TestName", "NA", 1, proxy)
            assert not result


def test_check_name_retries_on_429():
    with patch("scraper.requests.get") as mock_get:
        with patch("scraper.time.sleep") as mock_sleep:
            mock_fail = MagicMock()
            mock_fail.status_code = 429
            mock_success = MagicMock()
            mock_success.status_code = 200
            mock_success.text = "<li class='no_result'></li>"
            mock_get.side_effect = [mock_fail, mock_fail, mock_success]
            proxy = {
                "http": "http://999.888.777.666:4444",
                "https": "http://999.888.777.666:4444",
            }
            result = check_name("TestName", "NA", 1, proxy)
            assert result
            assert mock_get.call_count == 3


def test_check_name_returns_proxy_failed_when_no_proxy():
    result = check_name("TestName", "NA", 1, None)
    assert result == PROXY_FAILED


def test_check_name_returns_proxy_failed_on_exception():
    with patch("scraper.requests.get") as mock_get:
        with patch("scraper.time.sleep") as mock_sleep:
            mock_get.side_effect = Exception
            proxy = {
                "http": "http://999.888.777.666:4444",
                "https": "http://999.888.777.666:4444",
            }
            result = check_name("TestName", "NA", 1, proxy)
            assert result == PROXY_FAILED
