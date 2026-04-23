import re
from urllib.parse import quote
from crawler.base import BaseCrawler
from utils.http_client import fetch


class NaverBlogCrawler(BaseCrawler):
    """네이버 블로그 크롤러 (requests 기반, Selenium 불필요)"""

    site_name = "네이버블로그"

    def search_posts(self, board_url, keyword, max_pages):
        """네이버 통합검색(전체 블로그)에서 키워드를 검색합니다.

        검색 URL: https://search.naver.com/search.naver?where=blog&query=키워드&start=N
        board_url은 무시됩니다 (전체 검색).
        """
        posts = []
        seen_urls = set()
        encoded_kw = quote(keyword)
        blog_post_pattern = re.compile(r"^https://blog\.naver\.com/([^/?#]+)/(\d+)")

        for page in range(max_pages):
            start = page * 10 + 1
            url = f"https://search.naver.com/search.naver?where=blog&query={encoded_kw}&start={start}"

            soup = fetch(url, headers={"Referer": "https://search.naver.com/"})
            if soup is None:
                continue

            # 블로그 게시글 URL 패턴에 매칭되는 링크 수집
            url_to_title = {}
            for link in soup.select("a[href]"):
                href = link.get("href", "")
                m = blog_post_pattern.match(href)
                if not m:
                    continue
                clean_url = m.group()
                text = link.get_text(strip=True)
                if not text or text == "네이버 블로그":
                    continue
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

    def get_post_list(self, board_url, max_pages):
        """get_post_list는 통합검색 사이트이므로 사용하지 않습니다."""
        return []

    def get_post_detail(self, post_url):
        """네이버 블로그 게시글 상세 정보를 requests로 가져옵니다.

        PostView.naver URL을 직접 요청하여 iframe 없이 본문에 접근합니다.
        """
        # URL에서 blogId와 logNo 추출
        m = re.search(r"blog\.naver\.com/([^/?#]+)/(\d+)", post_url)
        if not m:
            return None

        blog_id = m.group(1)
        log_no = m.group(2)

        # PostView.naver로 직접 접근 (iframe 불필요)
        view_url = (
            f"https://blog.naver.com/PostView.naver?"
            f"blogId={blog_id}&logNo={log_no}"
            f"&redirect=Dlog&widgetTypeCall=true&directAccess=false"
        )

        soup = fetch(view_url)
        if soup is None:
            return None

        result = {
            "url": post_url, "title": "", "content": "", "date": "",
            "author": "", "author_ip": "", "comments": [],
        }

        # 제목
        for sel in ["div.se-title-text span", "span.pcol1", "div.htitle span", "h3.se_textarea"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                result["title"] = el.get_text(strip=True)
                break

        # 작성자
        for sel in ["span.nick", "a.link_nick", "span.blog_author"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                result["author"] = el.get_text(strip=True)
                break

        # 날짜
        for sel in ["span.se_publishDate", "p.date", "span.date"]:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                result["date"] = el.get_text(strip=True)
                break

        # 본문
        for sel in ["div.se-main-container", "div#postViewArea", "div.post_ct"]:
            el = soup.select_one(sel)
            if el:
                result["content"] = el.get_text(separator="\n", strip=True)
                break

        # 댓글 (블로그 댓글은 별도 AJAX로 로딩되므로 여기서는 수집하지 않음)

        return result
