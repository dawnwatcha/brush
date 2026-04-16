import time
import config
from utils.filters import matches_keywords


class BaseCrawler:
    """모든 사이트 크롤러의 공통 틀입니다."""

    site_name = "기본"

    def get_post_list(self, board_url, max_pages):
        """게시판에서 게시글 목록(url, title, date)을 가져옵니다."""
        raise NotImplementedError

    def search_posts(self, board_url, keyword, max_pages):
        """사이트의 검색 기능으로 키워드가 포함된 게시글 목록을 가져옵니다.

        구현하지 않은 사이트는 NotImplementedError를 발생시키고,
        그 경우 base.crawl()이 일반 목록 가져오기 + 필터링으로 자동 전환됩니다.
        """
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
        """전체 크롤링을 실행합니다.

        키워드가 있으면 사이트 검색 기능을 사용하고,
        키워드가 없으면 게시판 전체를 크롤링합니다.
        """
        if keywords is None:
            keywords = config.KEYWORDS
        if max_pages is None:
            max_pages = config.MAX_PAGES

        # 1단계: 게시글 목록 가져오기
        post_list = self._collect_post_list(board_url, keywords, max_pages)

        if not post_list:
            print("  게시글을 찾지 못했습니다.")
            return []

        # 2단계: 각 게시글 상세 정보 가져오기
        results = []
        total = len(post_list)
        failed = 0

        print(f"  {total}개의 게시글 상세 정보를 가져옵니다...")

        for i, post in enumerate(post_list, 1):
            print(f"  게시글 처리 중... ({i}/{total})", end="\r")

            try:
                detail = self.get_post_detail(post["url"])
                if detail is None:
                    failed += 1
                    continue

                # 사이트 검색이 부정확할 수 있으므로 본문/댓글까지 한번 더 확인
                if matches_keywords(detail, keywords):
                    results.append(detail)

            except Exception as e:
                print(f"\n  [경고] 게시글 처리 실패: {e}")
                failed += 1
                continue

        print(f"\n  완료: {len(results)}개 수집, {failed}개 실패")
        return results

    def _collect_post_list(self, board_url, keywords, max_pages):
        """키워드 유무에 따라 게시글 목록을 수집합니다."""
        # 키워드가 없으면 게시판 전체 가져오기
        if not keywords:
            print(f"\n[{self.site_name}] 게시판의 게시글 목록을 가져오는 중...")
            posts = self.get_post_list(board_url, max_pages)
            print(f"  {len(posts)}개의 게시글을 찾았습니다.")
            return posts

        # 키워드가 있으면 사이트 검색 기능 사용 시도
        print(f"\n[{self.site_name}] 사이트 검색 기능으로 키워드를 검색하는 중...")
        all_posts = []
        seen_urls = set()
        search_failed = False

        for keyword in keywords:
            try:
                print(f"  키워드 '{keyword}' 검색 중...")
                results = self.search_posts(board_url, keyword, max_pages)

                # URL 중복 제거 (여러 키워드에서 같은 글이 나올 수 있음)
                for post in results:
                    url = post.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_posts.append(post)

                print(f"    -> {len(results)}개 발견")

            except NotImplementedError:
                # 검색 미지원 사이트 - 일반 목록 + 필터링으로 자동 전환
                if not search_failed:
                    print(f"  [안내] 이 사이트는 자동 검색을 지원하지 않습니다.")
                    print(f"         게시판 전체를 가져온 뒤 키워드로 필터링합니다.")
                    search_failed = True
            except Exception as e:
                print(f"    [경고] 검색 실패: {e}")

        # 검색 미지원 사이트인 경우 폴백
        if search_failed:
            posts = self.get_post_list(board_url, max_pages)
            # 제목에 키워드가 들어간 글만 1차 필터링
            filtered = []
            for post in posts:
                title = post.get("title", "").lower()
                if any(kw.lower() in title for kw in keywords):
                    filtered.append(post)
            print(f"  전체 {len(posts)}개 중 제목 매칭 {len(filtered)}개")
            return filtered

        print(f"  중복 제거 후 총 {len(all_posts)}개의 게시글을 찾았습니다.")
        return all_posts
