from urllib.parse import quote, urlparse, parse_qs
from crawler.base import BaseCrawler
from utils.http_client import fetch


class FmkoreaCrawler(BaseCrawler):
    """에펨코리아 크롤러"""

    site_name = "에펨코리아"

    def search_posts(self, board_url, keyword, max_pages):
        """에펨코리아 게시판 내에서 키워드를 검색합니다.

        검색 URL 예시:
        https://www.fmkorea.com/index.php?mid=best&search_keyword=키워드&search_target=title_content
        """
        # 게시판 mid 추출
        # 예: https://www.fmkorea.com/best -> mid=best
        # 예: https://www.fmkorea.com/index.php?mid=football -> mid=football
        parsed = urlparse(board_url)
        mid = ""

        qs = parse_qs(parsed.query)
        if "mid" in qs:
            mid = qs["mid"][0]
        elif parsed.path and parsed.path != "/":
            # path가 /best 형식인 경우
            mid = parsed.path.strip("/").split("/")[0]

        if not mid:
            print("    [경고] 게시판 ID(mid)를 찾을 수 없습니다.")
            return []

        posts = []
        encoded_kw = quote(keyword)

        for page in range(1, max_pages + 1):
            url = (
                f"https://www.fmkorea.com/index.php?mid={mid}"
                f"&search_keyword={encoded_kw}&search_target=title_content&page={page}"
            )

            soup = fetch(url, headers={"Referer": "https://www.fmkorea.com/"})
            if soup is None:
                continue

            rows = soup.select("table.bd_lst tbody tr")
            if not rows:
                rows = soup.select("div.fm_best_widget li")

            found_in_page = 0
            for row in rows:
                try:
                    title_el = row.select_one("a.hx") or row.select_one("td.title a") or row.select_one("h3.title a")
                    if not title_el:
                        continue

                    href = title_el.get("href", "")
                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = "https://www.fmkorea.com" + href

                    title = title_el.get_text(strip=True)
                    author_el = row.select_one("a.member_plate") or row.select_one("span.author")
                    author = author_el.get_text(strip=True) if author_el else ""
                    date_el = row.select_one("span.regdate") or row.select_one("td.time")
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
        """에펨코리아 게시판에서 게시글 목록을 가져옵니다.

        board_url 예시: https://www.fmkorea.com/best
        """
        posts = []

        for page in range(1, max_pages + 1):
            url = f"{board_url}?page={page}" if "?" not in board_url else f"{board_url}&page={page}"
            print(f"  페이지 {page}/{max_pages} 가져오는 중...")

            soup = fetch(url, headers={"Referer": "https://www.fmkorea.com/"})
            if soup is None:
                continue

            # 게시글 목록
            rows = soup.select("li.li_best2_pop0, li.li_best2_pop1, li.li_best2_pop2")
            if not rows:
                rows = soup.select("table.bd_lst tbody tr")
            if not rows:
                rows = soup.select("div.fm_best_widget li")

            for row in rows:
                try:
                    title_el = row.select_one("a.hx") or row.select_one("h3.title a") or row.select_one("td.title a")
                    if not title_el:
                        continue

                    href = title_el.get("href", "")
                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = "https://www.fmkorea.com" + href

                    title = title_el.get_text(strip=True)

                    # 작성자
                    author_el = row.select_one("span.author") or row.select_one("a.member_plate")
                    author = author_el.get_text(strip=True) if author_el else ""

                    # 날짜
                    date_el = row.select_one("span.regdate") or row.select_one("td.time")
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
        """에펨코리아 게시글 상세 정보를 가져옵니다."""
        soup = fetch(post_url, headers={"Referer": "https://www.fmkorea.com/"})
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
        title_el = soup.select_one("span.np_18px_span") or soup.select_one("h1.np_18px")
        if title_el:
            result["title"] = title_el.get_text(strip=True)

        # 작성자
        author_el = soup.select_one("a.member_plate") or soup.select_one("span.author")
        if author_el:
            result["author"] = author_el.get_text(strip=True)

        # 날짜
        date_el = soup.select_one("span.date") or soup.select_one("div.top_area span.side")
        if date_el:
            result["date"] = date_el.get_text(strip=True)

        # 본문
        content_el = soup.select_one("div.xe_content") or soup.select_one("article")
        if content_el:
            result["content"] = content_el.get_text(separator="\n", strip=True)

        # 댓글
        comment_items = soup.select("div.fdb_lst_ul li.fdb_itm, div.comment_list li")
        for cmt in comment_items:
            try:
                c_author_el = cmt.select_one("a.member_plate") or cmt.select_one("span.author")
                c_content_el = cmt.select_one("div.xe_content") or cmt.select_one("div.comment_content")
                c_date_el = cmt.select_one("span.date") or cmt.select_one("span.time")

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
