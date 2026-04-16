import time
import re
from urllib.parse import quote
from crawler.base import BaseCrawler
import config


class NaverCafeCrawler(BaseCrawler):
    """네이버 카페 크롤러 (Selenium 사용)"""

    site_name = "네이버카페"

    def __init__(self):
        self.driver = None
        self._cafe_id = None  # 카페 숫자 ID 캐시

    def _get_cafe_id(self, board_url):
        """카페 URL에서 숫자 ID(clubid)를 가져옵니다."""
        from selenium.webdriver.common.by import By

        if self._cafe_id:
            return self._cafe_id

        # board_url에 이미 clubid가 있는 경우
        match = re.search(r"clubid=(\d+)", board_url)
        if match:
            self._cafe_id = match.group(1)
            return self._cafe_id

        # 없으면 카페 메인 페이지에 가서 가져오기
        self.driver.get(board_url)
        time.sleep(2)
        html = self.driver.page_source
        match = re.search(r"g_clubId\s*=\s*['\"]?(\d+)['\"]?", html)
        if not match:
            match = re.search(r"clubid=(\d+)", html)
        if match:
            self._cafe_id = match.group(1)
            return self._cafe_id

        return None

    def search_posts(self, board_url, keyword, max_pages):
        """네이버 카페 내에서 키워드를 검색합니다."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        self._ensure_driver()

        cafe_id = self._get_cafe_id(board_url)
        if not cafe_id:
            print("    [경고] 카페 ID를 찾을 수 없습니다.")
            return []

        # 카페 베이스 URL 추출 (예: https://cafe.naver.com/카페명)
        cafe_base = re.match(r"(https?://cafe\.naver\.com/[^/?]+)", board_url)
        cafe_base_url = cafe_base.group(1) if cafe_base else "https://cafe.naver.com"

        posts = []
        encoded_kw = quote(keyword)

        for page in range(1, max_pages + 1):
            search_url = (
                f"{cafe_base_url}?iframe_url_utf8=%2FArticleSearchList.nhn"
                f"%3Fsearch.clubid%3D{cafe_id}"
                f"%26search.searchBy%3D0"
                f"%26search.query%3D{encoded_kw}"
                f"%26search.page%3D{page}"
            )

            self.driver.get(search_url)
            time.sleep(2)

            try:
                self.driver.switch_to.default_content()
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "cafe_main"))
                )
                self.driver.switch_to.frame(iframe)
            except Exception:
                continue

            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "div.article-board a.article")
                if not rows:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table.board-box tr a.article")

                if not rows:
                    self.driver.switch_to.default_content()
                    break

                for row in rows:
                    try:
                        href = row.get_attribute("href") or ""
                        title = row.text.strip()
                        if href and title:
                            posts.append({"url": href, "title": title, "date": ""})
                    except Exception:
                        continue
            except Exception:
                pass

            self.driver.switch_to.default_content()

        return posts

    def _ensure_driver(self):
        """Selenium 드라이버를 준비하고 로그인합니다."""
        if self.driver is not None:
            return

        if not config.NAVER_ID or not config.NAVER_PW:
            raise ValueError(
                "네이버 카페 크롤링을 위해 config.py에 NAVER_ID와 NAVER_PW를 입력해주세요."
            )

        from utils.http_client import get_selenium_driver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        print("  Chrome 브라우저를 시작합니다...")
        self.driver = get_selenium_driver()

        # 네이버 로그인
        print("  네이버에 로그인 중...")
        self.driver.get("https://nid.naver.com/nidlogin.login")
        time.sleep(2)

        # JavaScript로 아이디/비밀번호 입력 (send_keys가 차단되는 경우 대비)
        self.driver.execute_script(
            f"document.getElementById('id').value = '{config.NAVER_ID}'"
        )
        self.driver.execute_script(
            f"document.getElementById('pw').value = '{config.NAVER_PW}'"
        )
        time.sleep(1)

        # 로그인 버튼 클릭
        login_btn = self.driver.find_element(By.ID, "log.login")
        login_btn.click()
        time.sleep(3)

        # 로그인 성공 확인
        if "nidlogin" in self.driver.current_url:
            print("  [경고] 로그인에 실패했을 수 있습니다. 캡차 인증이 필요할 수 있습니다.")

    def get_post_list(self, board_url, max_pages):
        """네이버 카페 게시판에서 게시글 목록을 가져옵니다.

        board_url 예시: https://cafe.naver.com/cafename?iframe_url=/ArticleList.nhn%3Fsearch.clubid=12345%26search.menuid=1%26search.boardtype=L
        또는: https://cafe.naver.com/ArticleList.nhn?search.clubid=12345&search.menuid=1
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        self._ensure_driver()
        posts = []

        for page in range(1, max_pages + 1):
            url = f"{board_url}&search.page={page}" if "?" in board_url else f"{board_url}?search.page={page}"
            print(f"  페이지 {page}/{max_pages} 가져오는 중...")

            self.driver.get(url)
            time.sleep(2)

            # cafe_main iframe으로 전환
            try:
                self.driver.switch_to.default_content()
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "cafe_main"))
                )
                self.driver.switch_to.frame(iframe)
            except Exception:
                print("  [경고] iframe 전환 실패")
                continue

            try:
                # 게시글 목록
                rows = self.driver.find_elements(By.CSS_SELECTOR, "div.article-board a.article")
                if not rows:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, "table.board-box tr a.article")

                for row in rows:
                    try:
                        href = row.get_attribute("href") or ""
                        title = row.text.strip()
                        if not href or not title:
                            continue

                        posts.append({
                            "url": href,
                            "title": title,
                            "date": "",
                        })
                    except Exception:
                        continue
            except Exception as e:
                print(f"  [경고] 목록 가져오기 실패: {e}")

            self.driver.switch_to.default_content()

        return posts

    def get_post_detail(self, post_url):
        """네이버 카페 게시글 상세 정보를 가져옵니다."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        self._ensure_driver()

        result = {
            "url": post_url,
            "title": "",
            "content": "",
            "date": "",
            "author": "",
            "author_ip": "",
            "comments": [],
        }

        self.driver.get(post_url)
        time.sleep(2)

        # cafe_main iframe 전환
        try:
            self.driver.switch_to.default_content()
            iframe = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "cafe_main"))
            )
            self.driver.switch_to.frame(iframe)
        except Exception:
            return None

        try:
            # 제목
            try:
                title_el = self.driver.find_element(By.CSS_SELECTOR, "h3.title_text")
                result["title"] = title_el.text.strip()
            except Exception:
                pass

            # 작성자
            try:
                author_el = self.driver.find_element(By.CSS_SELECTOR, "button.nickname, span.nickname")
                result["author"] = author_el.text.strip()
            except Exception:
                pass

            # 날짜
            try:
                date_el = self.driver.find_element(By.CSS_SELECTOR, "span.article_info span.date")
                result["date"] = date_el.text.strip()
            except Exception:
                pass

            # 본문
            try:
                content_el = self.driver.find_element(
                    By.CSS_SELECTOR, "div.se-main-container, div.ContentRenderer"
                )
                result["content"] = content_el.text.strip()
            except Exception:
                pass

            # 댓글
            try:
                comment_items = self.driver.find_elements(
                    By.CSS_SELECTOR, "ul.comment_list li.CommentItem"
                )
                for cmt in comment_items:
                    try:
                        c_author = ""
                        c_content = ""
                        c_date = ""

                        try:
                            c_author = cmt.find_element(
                                By.CSS_SELECTOR, "span.comment_nickname"
                            ).text.strip()
                        except Exception:
                            pass

                        try:
                            c_content = cmt.find_element(
                                By.CSS_SELECTOR, "span.text_comment"
                            ).text.strip()
                        except Exception:
                            pass

                        try:
                            c_date = cmt.find_element(
                                By.CSS_SELECTOR, "span.comment_info_date"
                            ).text.strip()
                        except Exception:
                            pass

                        if c_content:
                            result["comments"].append({
                                "author": c_author,
                                "author_ip": "",
                                "date": c_date,
                                "content": c_content,
                            })
                    except Exception:
                        continue
            except Exception:
                pass

        except Exception as e:
            print(f"  [경고] 상세 정보 가져오기 실패: {e}")

        self.driver.switch_to.default_content()
        return result

    def __del__(self):
        """드라이버를 정리합니다."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
