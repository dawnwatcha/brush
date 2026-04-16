from urllib.parse import quote
from crawler.base import BaseCrawler
from utils.http_client import fetch


class RuliwebCrawler(BaseCrawler):
    """루리웹 크롤러"""

    site_name = "루리웹"

    def search_posts(self, board_url, keyword, max_pages):
        """루리웹 게시판 내에서 키워드를 검색합니다.

        검색 URL: {board_url}?search_type=subject_content&search_key=키워드&page=N
        search_type:
          - subject: 제목만
          - subject_content: 제목+내용
          - nick: 글쓴이
        """
        # board_url에서 쿼리스트링 제거
        base_url = board_url.split("?")[0]

        posts = []
        encoded_kw = quote(keyword)

        for page in range(1, max_pages + 1):
            url = (
                f"{base_url}?page={page}"
                f"&search_type=subject_content&search_key={encoded_kw}"
            )

            soup = fetch(url)
            if soup is None:
                continue

            rows = soup.select("table.board_list_table tr.table_body, table.board_list_table tbody tr")
            if not rows:
                break

            found_in_page = 0
            for row in rows:
                try:
                    title_el = row.select_one("td.subject a.deco") or row.select_one("td.subject a")
                    if not title_el:
                        continue

                    href = title_el.get("href", "")
                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = "https://bbs.ruliweb.com" + href

                    title = title_el.get_text(strip=True)
                    author_el = row.select_one("td.writer a") or row.select_one("td.writer")
                    author = author_el.get_text(strip=True) if author_el else ""
                    date_el = row.select_one("td.time")
                    date = date_el.get_text(strip=True) if date_el else ""

                    posts.append({
                        "url": href,
                        "title": title,
                        "date": date,
                        "author": author,
                    })
                    found_in_page += 1
                except Exception:
                    continue

            if found_in_page == 0:
                break

        return posts

    def get_post_list(self, board_url, max_pages):
        """루리웹 게시판에서 게시글 목록을 가져옵니다.

        board_url 예시: https://bbs.ruliweb.com/community/board/300143
        """
        posts = []

        for page in range(1, max_pages + 1):
            url = f"{board_url}?page={page}" if "?" not in board_url else f"{board_url}&page={page}"
            print(f"  페이지 {page}/{max_pages} 가져오는 중...")

            soup = fetch(url)
            if soup is None:
                continue

            rows = soup.select("table.board_list_table tr.table_body, table.board_list_table tbody tr")

            for row in rows:
                try:
                    title_el = row.select_one("td.subject a.deco")
                    if not title_el:
                        title_el = row.select_one("td.subject a")
                    if not title_el:
                        continue

                    href = title_el.get("href", "")
                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = "https://bbs.ruliweb.com" + href

                    title = title_el.get_text(strip=True)

                    # 작성자
                    author_el = row.select_one("td.writer a") or row.select_one("td.writer")
                    author = author_el.get_text(strip=True) if author_el else ""

                    # 날짜
                    date_el = row.select_one("td.time")
                    date = date_el.get_text(strip=True) if date_el else ""

                    posts.append({
                        "url": href,
                        "title": title,
                        "date": date,
                        "author": author,
                    })
                except Exception:
                    continue

        return posts

    def get_post_detail(self, post_url):
        """루리웹 게시글 상세 정보를 가져옵니다."""
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
        title_el = soup.select_one("h4.subject_inner_text span.subject_text") or soup.select_one("h4.subject_text")
        if title_el:
            result["title"] = title_el.get_text(strip=True)

        # 작성자
        author_el = soup.select_one("span.nick a") or soup.select_one("div.user_info span.nick")
        if author_el:
            result["author"] = author_el.get_text(strip=True)

        # 날짜
        date_el = soup.select_one("span.regdate") or soup.select_one("div.user_info span.time")
        if date_el:
            result["date"] = date_el.get_text(strip=True)

        # 본문
        content_el = soup.select_one("div.view_content") or soup.select_one("div.board_main_view")
        if content_el:
            result["content"] = content_el.get_text(separator="\n", strip=True)

        # 댓글
        comment_items = soup.select("div.comment_view table.comment_table tbody tr, div.comment_element")
        for cmt in comment_items:
            try:
                c_author_el = cmt.select_one("span.nick a") or cmt.select_one("a.nick")
                c_content_el = cmt.select_one("td.comment span.text_wrapper") or cmt.select_one("div.comment_content")
                c_date_el = cmt.select_one("span.time") or cmt.select_one("td.time")

                if not c_content_el:
                    continue

                result["comments"].append({
                    "author": c_author_el.get_text(strip=True) if c_author_el else "",
                    "author_ip": "",
                    "date": c_date_el.get_text(strip=True) if c_date_el else "",
                    "content": c_content_el.get_text(separator="\n", strip=True),
                })
            except Exception:
                continue

        return result
