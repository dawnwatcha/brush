from urllib.parse import quote
from crawler.base import BaseCrawler
from utils.http_client import fetch, session as http_session


class RuliwebCrawler(BaseCrawler):
    """루리웹 크롤러"""

    site_name = "루리웹"

    def search_posts(self, board_url, keyword, max_pages):
        """루리웹 전체 사이트에서 키워드를 검색합니다.

        검색 URL: https://bbs.ruliweb.com/search?q=키워드
        board_url은 무시됩니다 (전체 검색).
        쿠키가 필요하므로 메인 페이지를 먼저 방문합니다.
        """
        # 쿠키 획득을 위해 메인 페이지 방문
        try:
            http_session.get("https://bbs.ruliweb.com/", timeout=10)
        except Exception:
            pass

        posts = []
        seen_urls = set()
        encoded_kw = quote(keyword)

        for page in range(1, max_pages + 1):
            url = f"https://bbs.ruliweb.com/search?q={encoded_kw}&page={page}"

            soup = fetch(url, headers={"Referer": "https://bbs.ruliweb.com/"})
            if soup is None:
                continue

            # "게시글" 섹션에서 결과 추출
            found_in_page = 0
            for section in soup.select("div.search_result"):
                title_el = section.select_one(".search_result_title")
                section_title = title_el.get_text(strip=True) if title_el else ""
                if "결과 없음" in section_title:
                    continue

                for link in section.select("a[href]"):
                    try:
                        href = link.get("href", "")
                        if "/read/" not in href or "#cmt" in href:
                            continue
                        if not href.startswith("http"):
                            href = "https://bbs.ruliweb.com" + href

                        title = link.get_text(strip=True)
                        if not title or href in seen_urls:
                            continue
                        seen_urls.add(href)

                        posts.append({
                            "url": href,
                            "title": title,
                            "date": "",
                            "author": "",
                        })
                        found_in_page += 1
                    except Exception:
                        continue

            if found_in_page == 0:
                break

        return posts

    def get_post_list(self, board_url, max_pages):
        """루리웹 게시판에서 게시글 목록을 가져옵니다."""
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

                    posts.append({"url": href, "title": title, "date": date, "author": author})
                except Exception:
                    continue

        return posts

    def get_post_detail(self, post_url):
        """루리웹 게시글 상세 정보를 가져옵니다."""
        soup = fetch(post_url)
        if soup is None:
            return None

        result = {
            "url": post_url, "title": "", "content": "", "date": "",
            "author": "", "author_ip": "", "comments": [],
        }

        title_el = soup.select_one("h4.subject_inner_text span.subject_text") or soup.select_one("h4.subject_text")
        if title_el:
            result["title"] = title_el.get_text(strip=True)

        author_el = soup.select_one("span.nick a") or soup.select_one("div.user_info span.nick")
        if author_el:
            result["author"] = author_el.get_text(strip=True)

        date_el = soup.select_one("span.regdate") or soup.select_one("div.user_info span.time")
        if date_el:
            result["date"] = date_el.get_text(strip=True)

        content_el = soup.select_one("div.view_content") or soup.select_one("div.board_main_view")
        if content_el:
            result["content"] = content_el.get_text(separator="\n", strip=True)

        for cmt in soup.select("div.comment_view table.comment_table tbody tr, div.comment_element"):
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
