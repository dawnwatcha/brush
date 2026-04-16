import time
import re
from urllib.parse import quote, urlparse
from crawler.base import BaseCrawler
from utils.http_client import fetch
import config


class NaverBlogCrawler(BaseCrawler):
    """네이버 블로그 크롤러 (Selenium 사용)"""

    site_name = "네이버블로그"

    def __init__(self):
        self.driver = None

    def search_posts(self, board_url, keyword, max_pages):
        """네이버 통합검색(전체 네이버 블로그)에서 키워드를 검색합니다.

        검색 URL: https://search.naver.com/search.naver?where=blog&query=키워드&start=N
        start는 1, 11, 21, ... (페이지당 10개)
        board_url은 무시됩니다.
        """
        posts = []
        seen_urls = set()
        encoded_kw = quote(keyword)
        blog_post_pattern = re.compile(r"^https://blog\.naver\.com/[^/?#]+/\d+")

        for page in range(max_pages):
            start = page * 10 + 1
            url = (
                f"https://search.naver.com/search.naver?"
                f"where=blog&query={encoded_kw}&start={start}"
            )

            soup = fetch(url, headers={"Referer": "https://search.naver.com/"})
            if soup is None:
                continue

            # 블로그 게시글 URL 패턴에 매칭되는 모든 링크 수집
            # 같은 URL에 여러 번 링크가 있을 수 있으므로 가장 긴 텍스트(= 제목)를 고름
            url_to_title = {}
            for link in soup.select("a[href]"):
                href = link.get("href", "")
                m = blog_post_pattern.match(href)
                if not m:
                    continue
                clean_url = m.group()
                text = link.get_text(strip=True)
                if not text or "네이버 블로그" in text:
                    continue
                # 더 긴 제목으로 교체
                if clean_url not in url_to_title or len(text) > len(url_to_title[clean_url]):
                    url_to_title[clean_url] = text

            found_in_page = 0
            for clean_url, title in url_to_title.items():
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)
                posts.append({"url": clean_url, "title": title, "date": ""})
                found_in_page += 1

            if found_in_page == 0:
                break

        return posts

    def _ensure_driver(self):
        """Selenium 드라이버를 준비합니다."""
        if self.driver is not None:
            return

        from utils.http_client import get_selenium_driver

        print("  Chrome 브라우저를 시작합니다...")
        self.driver = get_selenium_driver()

    def get_post_list(self, board_url, max_pages):
        """네이버 블로그에서 게시글 목록을 가져옵니다.

        board_url 예시: https://blog.naver.com/blogid
        또는 카테고리: https://blog.naver.com/PostList.naver?blogId=xxx&categoryNo=1
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        self._ensure_driver()
        posts = []

        for page in range(1, max_pages + 1):
            url = f"{board_url}&currentPage={page}" if "?" in board_url else f"{board_url}?currentPage={page}"
            print(f"  페이지 {page}/{max_pages} 가져오는 중...")

            self.driver.get(url)
            time.sleep(2)

            # mainFrame iframe 전환
            try:
                self.driver.switch_to.default_content()
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "mainFrame"))
                )
                self.driver.switch_to.frame(iframe)
            except Exception:
                # iframe이 없는 새 블로그 형태일 수 있음
                pass

            try:
                # 게시글 링크 찾기
                links = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "a.url, span.title a, a.pcol2, table.board-box a"
                )

                for link in links:
                    try:
                        href = link.get_attribute("href") or ""
                        title = link.text.strip()
                        if not href or not title or "PostList" in href:
                            continue
                        if "blog.naver.com" not in href:
                            continue

                        posts.append({
                            "url": href,
                            "title": title,
                            "date": "",
                        })
                    except Exception:
                        continue
            except Exception:
                pass

            self.driver.switch_to.default_content()

        return posts

    def get_post_detail(self, post_url):
        """네이버 블로그 게시글 상세 정보를 가져옵니다."""
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

        # mainFrame iframe 전환
        try:
            self.driver.switch_to.default_content()
            iframe = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "mainFrame"))
            )
            self.driver.switch_to.frame(iframe)
        except Exception:
            pass

        try:
            # 제목
            try:
                title_el = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div.se-module-text h3, span.pcol1, div.htitle span"
                )
                result["title"] = title_el.text.strip()
            except Exception:
                pass

            # 작성자
            try:
                author_el = self.driver.find_element(
                    By.CSS_SELECTOR, "span.blog_author, nick a"
                )
                result["author"] = author_el.text.strip()
            except Exception:
                pass

            # 날짜
            try:
                date_el = self.driver.find_element(
                    By.CSS_SELECTOR, "span.se_publishDate, p.date"
                )
                result["date"] = date_el.text.strip()
            except Exception:
                pass

            # 본문
            try:
                content_el = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div.se-main-container, div.post-view, div#postViewArea"
                )
                result["content"] = content_el.text.strip()
            except Exception:
                pass

            # 댓글 (블로그 댓글 영역으로 전환)
            try:
                self.driver.switch_to.default_content()
                # 댓글 iframe
                comment_frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='comment']")
                if comment_frames:
                    self.driver.switch_to.frame(comment_frames[0])

                comment_items = self.driver.find_elements(
                    By.CSS_SELECTOR, "li.u_cbox_comment"
                )
                for cmt in comment_items:
                    try:
                        c_author = ""
                        c_content = ""
                        c_date = ""

                        try:
                            c_author = cmt.find_element(
                                By.CSS_SELECTOR, "span.u_cbox_nick"
                            ).text.strip()
                        except Exception:
                            pass

                        try:
                            c_content = cmt.find_element(
                                By.CSS_SELECTOR, "span.u_cbox_contents"
                            ).text.strip()
                        except Exception:
                            pass

                        try:
                            c_date = cmt.find_element(
                                By.CSS_SELECTOR, "span.u_cbox_date"
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
