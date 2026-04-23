from urllib.parse import quote, urlparse
from crawler.base import BaseCrawler
from utils.http_client import fetch


class ClienCrawler(BaseCrawler):
    """클리앙 크롤러"""

    site_name = "클리앙"

    def search_posts(self, board_url, keyword, max_pages):
        """클리앙 전체 사이트에서 키워드를 검색합니다.

        검색 URL: https://www.clien.net/service/search?q=키워드&sort=recency
        board_url은 무시됩니다 (전체 검색).
        """
        posts = []
        encoded_kw = quote(keyword)

        for page in range(max_pages):
            url = f"https://www.clien.net/service/search?q={encoded_kw}&sort=recency&p={page}"

            soup = fetch(url)
            if soup is None:
                continue

            items = soup.select("div.list_item, div.total_search div.list_item")

            for item in items:
                try:
                    link_el = item.select_one("a.list_subject") or item.select_one("a")
                    if not link_el or not link_el.get("href"):
                        continue

                    href = link_el["href"]
                    if not href.startswith("http"):
                        href = "https://www.clien.net" + href

                    title_el = item.select_one("span.subject_fixed") or link_el
                    title = title_el.get_text(strip=True)

                    date_el = item.select_one("span.timestamp") or item.select_one("span.time")
                    date = date_el.get_text(strip=True) if date_el else ""

                    posts.append({"url": href, "title": title, "date": date})
                except Exception:
                    continue

            if not items:
                break

        return posts

    def get_post_list(self, board_url, max_pages):
        """클리앙 게시판에서 게시글 목록을 가져옵니다.

        board_url 예시: https://www.clien.net/service/board/park
        """
        posts = []

        for page in range(max_pages):
            url = f"{board_url}?po={page}"
            print(f"  페이지 {page + 1}/{max_pages} 가져오는 중...")

            soup = fetch(url)
            if soup is None:
                continue

            # 게시글 목록 항목들
            items = soup.select("div.list_item")
            if not items:
                # 다른 구조 시도
                items = soup.select("div.contents_jirum")

            for item in items:
                try:
                    # 제목과 링크
                    title_el = item.select_one("span.subject_fixed")
                    if not title_el:
                        title_el = item.select_one("a.list_subject")
                    if not title_el:
                        continue

                    link_el = item.select_one("a.list_subject") or item.select_one("a")
                    if not link_el or not link_el.get("href"):
                        continue

                    href = link_el["href"]
                    if not href.startswith("http"):
                        href = "https://www.clien.net" + href

                    title = title_el.get_text(strip=True)

                    # 날짜
                    date_el = item.select_one("span.timestamp") or item.select_one("span.time")
                    date = date_el.get_text(strip=True) if date_el else ""

                    posts.append({
                        "url": href,
                        "title": title,
                        "date": date,
                    })
                except Exception:
                    continue

        return posts

    def get_post_detail(self, post_url):
        """클리앙 게시글 상세 정보를 가져옵니다."""
        soup = fetch(post_url)
        if soup is None:
            return None

        result = {
            "url": post_url,
            "title": "",
            "content": "",
            "date": "",
            "author": "",
            "author_ip": "",
            "comments": [],
        }

        # 제목
        title_el = soup.select_one("h3.post_subject span") or soup.select_one("h3.post_subject")
        if title_el:
            result["title"] = title_el.get_text(strip=True)

        # 작성자
        author_el = soup.select_one("span.nickname") or soup.select_one("span.contact_name")
        if author_el:
            result["author"] = author_el.get_text(strip=True)

        # 날짜
        date_el = soup.select_one("span.post_time") or soup.select_one("div.post_view span.time")
        if date_el:
            result["date"] = date_el.get_text(strip=True)

        # 본문
        content_el = soup.select_one("div.post_article") or soup.select_one("div.post_content")
        if content_el:
            result["content"] = content_el.get_text(separator="\n", strip=True)

        # 댓글
        comment_items = soup.select("div.comment_row")
        for comment in comment_items:
            try:
                c_author_el = comment.select_one("span.nickname") or comment.select_one("span.contact_name")
                c_content_el = comment.select_one("div.comment_content") or comment.select_one("div.comment_view")
                c_date_el = comment.select_one("span.timestamp") or comment.select_one("span.time")

                result["comments"].append({
                    "author": c_author_el.get_text(strip=True) if c_author_el else "",
                    "author_ip": "",
                    "date": c_date_el.get_text(strip=True) if c_date_el else "",
                    "content": c_content_el.get_text(separator="\n", strip=True) if c_content_el else "",
                })
            except Exception:
                continue

        return result
