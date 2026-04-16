import time
import config
from utils.filters import matches_keywords


class BaseCrawler:
    """모든 사이트 크롤러의 공통 틀입니다."""

    site_name = "기본"

    def get_post_list(self, board_url, max_pages):
        """게시판에서 게시글 목록(url, title, date)을 가져옵니다."""
        raise NotImplementedError

    def get_post_detail(self, post_url):
        """게시글 상세 페이지에서 정보를 가져옵니다.

        반환 형태:
        {
            "title": "제목",
            "content": "본문",
            "date": "2026-04-16",
            "author": "작성자",
            "author_ip": "123.456.*.*",
            "url": "https://...",
            "comments": [
                {"author": "댓글작성자", "author_ip": "", "date": "2026-04-16", "content": "댓글내용"},
                ...
            ]
        }
        """
        raise NotImplementedError

    def crawl(self, board_url, keywords=None, max_pages=None):
        """전체 크롤링을 실행합니다."""
        if keywords is None:
            keywords = config.KEYWORDS
        if max_pages is None:
            max_pages = config.MAX_PAGES

        print(f"\n[{self.site_name}] 게시글 목록을 가져오는 중...")
        post_list = self.get_post_list(board_url, max_pages)

        if not post_list:
            print("  게시글을 찾지 못했습니다.")
            return []

        print(f"  {len(post_list)}개의 게시글을 찾았습니다.")

        # 1단계: 제목에서 키워드 필터링 (빠른 필터)
        if keywords:
            filtered = []
            for post in post_list:
                title = post.get("title", "").lower()
                if any(kw.lower() in title for kw in keywords):
                    filtered.append(post)
            print(f"  제목 필터링 후: {len(filtered)}개")
        else:
            filtered = post_list

        # 2단계: 각 게시글 상세 정보 가져오기
        results = []
        total = len(filtered)
        failed = 0

        for i, post in enumerate(filtered, 1):
            print(f"  게시글 처리 중... ({i}/{total})", end="\r")

            try:
                detail = self.get_post_detail(post["url"])
                if detail is None:
                    failed += 1
                    continue

                # 2단계 필터링: 본문 + 댓글에서 키워드 확인
                if matches_keywords(detail, keywords):
                    results.append(detail)

            except Exception as e:
                print(f"\n  [경고] 게시글 처리 실패: {e}")
                failed += 1
                continue

        print(f"\n  완료: {len(results)}개 수집, {failed}개 실패")
        return results
