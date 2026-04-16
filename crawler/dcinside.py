import re
from crawler.base import BaseCrawler
from utils.http_client import fetch, fetch_json
import config


class DcinsideCrawler(BaseCrawler):
    """디시인사이드 크롤러"""

    site_name = "디시인사이드"

    def get_post_list(self, board_url, max_pages):
        """디시인사이드 갤러리에서 게시��� 목록을 가져옵니다.

        board_url 예시: https://gall.dcinside.com/board/lists/?id=programming
        또는 갤러리 ID만: programming
        """
        # URL이 아닌 갤러리 ID만 입력한 경우 처���
        if not board_url.startswith("http"):
            board_url = f"https://gall.dcinside.com/board/lists/?id={board_url}"

        # 갤러리 ID 추출
        gallery_id = ""
        if "id=" in board_url:
            gallery_id = board_url.split("id=")[1].split("&")[0]

        posts = []

        for page in range(1, max_pages + 1):
            url = f"{board_url}&page={page}" if "?" in board_url else f"{board_url}?page={page}"
            print(f"  페이지 {page}/{max_pages} 가져오는 중...")

            soup = fetch(
                url,
                delay=config.DC_REQUEST_DELAY,
                headers={"Referer": "https://gall.dcinside.com/"},
            )
            if soup is None:
                continue

            rows = soup.select("tr.ub-content.us-post")

            for row in rows:
                try:
                    # 공지사항 제외
                    num_el = row.select_one("td.gall_num")
                    if num_el and num_el.get_text(strip=True) in ("공지", "설문", "AD"):
                        continue

                    title_el = row.select_one("td.gall_tit a:not(.reply_numbox)")
                    if not title_el:
                        continue

                    href = title_el.get("href", "")
                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = "https://gall.dcinside.com" + href

                    title = title_el.get_text(strip=True)

                    # 작성자 및 IP
                    writer_el = row.select_one("td.gall_writer")
                    author = ""
                    author_ip = ""
                    if writer_el:
                        author = writer_el.get("data-nick", "")
                        author_ip = writer_el.get("data-ip", "")

                    # 날짜
                    date_el = row.select_one("td.gall_date")
                    date = date_el.get("title", "") if date_el else ""
                    if not date:
                        date = date_el.get_text(strip=True) if date_el else ""

                    posts.append({
                        "url": href,
                        "title": title,
                        "date": date,
                        "author": author,
                        "author_ip": author_ip,
                    })
                except Exception:
                    continue

        return posts

    def get_post_detail(self, post_url):
        """디시인사이드 게시글 상세 정보를 가져옵니다."""
        soup = fetch(
            post_url,
            delay=config.DC_REQUEST_DELAY,
            headers={"Referer": "https://gall.dcinside.com/"},
        )
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
        title_el = soup.select_one("span.title_subject")
        if title_el:
            result["title"] = title_el.get_text(strip=True)

        # 작성자 및 IP
        writer_el = soup.select_one("div.gall_writer")
        if writer_el:
            result["author"] = writer_el.get("data-nick", "")
            result["author_ip"] = writer_el.get("data-ip", "")

        # 날짜
        date_el = soup.select_one("span.gall_date")
        if date_el:
            result["date"] = date_el.get("title", "") or date_el.get_text(strip=True)

        # 본문
        content_el = soup.select_one("div.write_div") or soup.select_one("div.writing_view_box")
        if content_el:
            # 광고 요소 제거
            for ad in content_el.select("div.og-div, div.ad_bottom_list"):
                ad.decompose()
            result["content"] = content_el.get_text(separator="\n", strip=True)

        # 댓글 가져오기 (AJAX)
        result["comments"] = self._get_comments(soup, post_url)

        return result

    def _get_comments(self, soup, post_url):
        """디시인사이드 댓글을 AJAX로 가져옵니다."""
        comments = []

        # 갤러리 ID와 게시글 번호 추출
        gallery_id = ""
        post_no = ""

        id_match = re.search(r"id=([^&]+)", post_url)
        if id_match:
            gallery_id = id_match.group(1)

        no_match = re.search(r"no=(\d+)", post_url)
        if no_match:
            post_no = no_match.group(1)

        if not gallery_id or not post_no:
            return comments

        # e_s_n_o 토큰 추출
        e_s_n_o = ""
        script_tags = soup.select("script")
        for script in script_tags:
            text = script.string or ""
            match = re.search(r"e_s_n_o\s*=\s*['\"]([^'\"]+)['\"]", text)
            if match:
                e_s_n_o = match.group(1)
                break

        # 댓글 페이지를 가져옴
        comment_url = "https://gall.dcinside.com/board/comment/"
        for page in range(1, 6):  # 댓글 최대 5페이지
            data = {
                "id": gallery_id,
                "no": post_no,
                "cmt_id": gallery_id,
                "cmt_no": post_no,
                "comment_page": str(page),
                "e_s_n_o": e_s_n_o,
                "_GALLTYPE_": "G",
            }

            json_data = fetch_json(
                comment_url,
                delay=config.DC_REQUEST_DELAY,
                headers={"Referer": post_url},
                data=data,
            )

            if not json_data or "comments" not in json_data:
                break

            comment_list = json_data.get("comments", [])
            if not comment_list:
                break

            for cmt in comment_list:
                try:
                    # 답글이 아닌 삭제된 댓글 건너뛰기
                    if cmt.get("del_yn") == "Y":
                        continue

                    comments.append({
                        "author": cmt.get("name", ""),
                        "author_ip": cmt.get("ip", ""),
                        "date": cmt.get("reg_date", ""),
                        "content": cmt.get("memo", "").strip(),
                    })
                except Exception:
                    continue

            # 더 이상 댓글이 없으면 중단
            total = json_data.get("total_cnt", 0)
            if isinstance(total, str):
                total = int(total) if total.isdigit() else 0
            if len(comments) >= total:
                break

        return comments
