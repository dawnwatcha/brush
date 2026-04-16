from crawler.base import BaseCrawler
from utils.http_client import fetch


class PpomppuCrawler(BaseCrawler):
    """뽐뿌 크롤러"""

    site_name = "뽐뿌"

    def get_post_list(self, board_url, max_pages):
        """뽐뿌 게시판에서 게시글 목록을 가져옵니다.

        board_url 예시: https://www.ppomppu.co.kr/zboard/zboard.php?id=freeboard
        """
        posts = []

        for page in range(1, max_pages + 1):
            url = f"{board_url}&page={page}" if "?" in board_url else f"{board_url}?page={page}"
            print(f"  페이지 {page}/{max_pages} 가져오는 중...")

            soup = fetch(url, encoding="utf-8")
            if soup is None:
                continue

            rows = soup.select("tr.baseList-border-bottom, tr.baseList-line")
            if not rows:
                rows = soup.select("table#revolution_main_table tr")

            for row in rows:
                try:
                    title_el = row.select_one("a.baseList-title") or row.select_one("td.baseList-space a.list_b")
                    if not title_el:
                        continue

                    href = title_el.get("href", "")
                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = "https://www.ppomppu.co.kr/zboard/" + href

                    title = title_el.get_text(strip=True)

                    # 작성자
                    author_el = row.select_one("span.baseList-name") or row.select_one("td.baseList-nw a")
                    author = author_el.get_text(strip=True) if author_el else ""

                    # 날짜
                    date_el = row.select_one("td.baseList-space time") or row.select_one("td.baseList-nw")
                    date = ""
                    if date_el:
                        time_tag = date_el.select_one("time")
                        if time_tag:
                            date = time_tag.get_text(strip=True)
                        else:
                            date = date_el.get_text(strip=True)

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
        """뽐뿌 게시글 상세 정보를 가져옵니다."""
        soup = fetch(post_url, encoding="utf-8")
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
        title_el = soup.select_one("h2.view_title") or soup.select_one("td.view_title font")
        if title_el:
            result["title"] = title_el.get_text(strip=True)

        # 작성자 및 IP
        author_el = soup.select_one("span.view_name") or soup.select_one("td.view_name a")
        if author_el:
            result["author"] = author_el.get_text(strip=True)

        # 뽐뿌는 일부 게시글에서 IP를 표시합니다
        ip_el = soup.select_one("span.view_ip")
        if ip_el:
            result["author_ip"] = ip_el.get_text(strip=True)

        # 날짜
        date_el = soup.select_one("span.view_date") or soup.select_one("td.view_date")
        if date_el:
            result["date"] = date_el.get_text(strip=True)

        # 본문
        content_el = soup.select_one("td.board-contents") or soup.select_one("div.board-contents")
        if content_el:
            result["content"] = content_el.get_text(separator="\n", strip=True)

        # 댓글
        comment_rows = soup.select("div.comment-item, tr.comment_line")
        for cmt in comment_rows:
            try:
                c_author_el = cmt.select_one("span.comment-name a") or cmt.select_one("a.comment_name")
                c_content_el = cmt.select_one("div.comment-text") or cmt.select_one("td.comment")
                c_date_el = cmt.select_one("span.comment-date") or cmt.select_one("td.comment_date")
                c_ip_el = cmt.select_one("span.comment-ip")

                result["comments"].append({
                    "author": c_author_el.get_text(strip=True) if c_author_el else "",
                    "author_ip": c_ip_el.get_text(strip=True) if c_ip_el else "",
                    "date": c_date_el.get_text(strip=True) if c_date_el else "",
                    "content": c_content_el.get_text(separator="\n", strip=True) if c_content_el else "",
                })
            except Exception:
                continue

        return result
