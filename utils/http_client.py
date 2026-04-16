import time
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
import config


_last_request_time = 0


def create_session():
    """재시도 기능이 포함된 HTTP 세션을 생성합니다."""
    session = requests.Session()
    session.headers.update(config.DEFAULT_HEADERS)

    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# 프로그램 전체에서 공유하는 세션
session = create_session()


def fetch(url, delay=None, encoding=None, headers=None):
    """URL에서 HTML을 가져와 BeautifulSoup 객체로 반환합니다."""
    global _last_request_time

    if delay is None:
        delay = config.REQUEST_DELAY

    # 요청 간격 유지
    elapsed = time.time() - _last_request_time
    if elapsed < delay:
        time.sleep(delay - elapsed)

    merged_headers = {}
    if headers:
        merged_headers.update(headers)

    try:
        response = session.get(url, headers=merged_headers, timeout=30)
        _last_request_time = time.time()

        if encoding:
            response.encoding = encoding
        elif response.apparent_encoding:
            response.encoding = response.apparent_encoding

        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "알 수 없음"
        if status == 403:
            print(f"  [오류] 접근이 차단되었습니다 (403). 30초 후 재시도합니다...")
            time.sleep(30)
            try:
                response = session.get(url, headers=merged_headers, timeout=30)
                _last_request_time = time.time()
                if encoding:
                    response.encoding = encoding
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except Exception:
                print(f"  [오류] 재시도 실패. 이 페이지를 건너뜁니다: {url}")
                return None
        else:
            print(f"  [오류] HTTP {status} 오류: {url}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"  [오류] 연결 실패: {url}")
        return None

    except requests.exceptions.Timeout:
        print(f"  [오류] 시간 초과: {url}")
        return None

    except Exception as e:
        print(f"  [오류] 예상치 못한 오류: {e}")
        return None


def fetch_json(url, delay=None, headers=None, data=None):
    """URL에서 JSON 데이터를 가져옵니다 (POST 요청 지원)."""
    global _last_request_time

    if delay is None:
        delay = config.REQUEST_DELAY

    elapsed = time.time() - _last_request_time
    if elapsed < delay:
        time.sleep(delay - elapsed)

    merged_headers = {"X-Requested-With": "XMLHttpRequest"}
    if headers:
        merged_headers.update(headers)

    try:
        if data is not None:
            response = session.post(url, headers=merged_headers, data=data, timeout=30)
        else:
            response = session.get(url, headers=merged_headers, timeout=30)

        _last_request_time = time.time()
        response.raise_for_status()
        return response.json()

    except Exception as e:
        print(f"  [오류] JSON 요청 실패: {e}")
        return None


def get_selenium_driver():
    """Selenium Chrome 드라이버를 생성합니다."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=ko-KR")
    options.add_argument(
        f"user-agent={config.DEFAULT_HEADERS['User-Agent']}"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver
