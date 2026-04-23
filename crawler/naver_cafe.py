import re
from urllib.parse import quote
from crawler.base import BaseCrawler
from utils.http_client import fetch


class NaverCafeCrawler(BaseCrawler):
    """네이버 카페 크롤러 (requests 기반, 로그인/Selenium 불필요)

    네이버 통합검색의 카페 탭을 사용하여 공개 카페 게시글을 수집합니다.
    로그인이 필요 없어 웹 배포 환경에서도 동작합니다.

    제한사항:
    - 비공개 카페 게시글은 검색 결과에 노출되지 않습니다.
    - 게시글 본문은 검색 결과의 미리보기 텍스트로 대체됩니다.
      (카페 본문 직접 접근은 대부분 로그인이 필요합니다.)
    """

    site_name = "네이버카페"

    def search_posts(self, board_url, keyword, max_pages):
        """네이버 통합검색 카페 탭에서 키워드를 검색합니다.

        검색 URL: https://search.naver.com/search.naver?ssc=tab.cafe.all&query=키워드&start=N
        board_url은 무시됩니다 (전체 검색).
        """
        posts = []
        seen_urls = set()
        encoded_kw = quote(keyword)
        cafe_post_pattern = re.compile(r"^https://cafe\.naver\.com/([^/?#]+)/(\d+)")

        for page in range(max_pages):
            start = page * 10 + 1
            url = (
                f"https://search.naver.com/search.naver?"
                f"ssc=tab.cafe.all&query={encoded_kw}&start={start}"
            )

            soup = fetch(url, headers={"Referer": "https://search.naver.com/"})
            if soup is None:
                continue

            # 카페 게시글 URL과 제목 추출
            url_to_info = {}
            for link in soup.select("a[href]"):
                href = link.get("href", "")
                m = cafe_post_pattern.match(href)
                if not m:
                    continue
                clean_url = m.group()
                text = link.get_text(strip=True)
                if not text:
                    continue
                # 가장 긴 텍스트(= 제목)를 채택
                if clean_url not in url_to_info or len(text) > len(url_to_info[clean_url]):
                    url_to_info[clean_url] = text

            found_in_page = 0
            for clean_url, title in url_to_info.items():
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)
                posts.append({"url": clean_url, "title": title, "date": ""})
                found_in_page += 1

            if found_in_page == 0:
                break

        return posts

    def get_post_list(self, board_url, max_pages):
        """get_post_list는 통합검색 사이트이므로 사용하지 않습니다."""
        return []

    def get_post_detail(self, post_url):
        """네이버 카페 게시글 정보를 가져옵니다.

        카페 본문은 대부분 로그인이 필요하므로,
        모바일 페이지에서 가능한 만큼 추출을 시도하고,
        실패 시 검색 결과에서 가져온 제목만 반환합니다.
        """
        result = {
            "url": post_url, "title": "", "content": "", "date": "",
            "author": "", "author_ip": "", "comments": [],
        }

        # 모바일 URL로 시도 (접근 가능성이 높음)
        m = re.search(r"cafe\.naver\.com/([^/?#]+)/(\d+)", post_url)
        if not m:
            return result

        cafe_name = m.group(1)
        article_id = m.group(2)
        mobile_url = f"https://m.cafe.naver.com/{cafe_name}/{article_id}"

        soup = fetch(mobile_url, headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://m.search.naver.com/",
        })

        if soup is None:
            return result

        # 제목
        for sel in ["h2.tit", "h3.title_text", "div.tit_area h2", "p.tit"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                result["title"] = el.get_text(strip=True)
                break

        # 작성자
        for sel in ["span.nick", "a.nick", "div.profile_area span.nick"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                result["author"] = el.get_text(strip=True)
                break

        # 날짜
        for sel in ["span.date", "div.date", "span.time"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                result["date"] = el.get_text(strip=True)
                break

        # 본문
        for sel in ["div.post_content", "div.se-main-container", "div#postContent", "div.ContentRenderer"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                result["content"] = el.get_text(separator="\n", strip=True)
                break

        # 본문이 비어있으면 (로그인 필요 카페)
        if not result["content"]:
            result["content"] = "(비공개 카페 또는 로그인 필요 - 검색 결과 제목만 수집됨)"

        return result
