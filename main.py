# -*- coding: utf-8 -*-
"""
Brush - 한국 커뮤니티 웹 크롤러
"""

import sys
import io

# Windows 콘솔에서 한글 출력 문제 해결
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import config
from utils.excel_writer import save_to_excel


SITES = {
    "1": {
        "name": "네이버 카페",
        "class": "crawler.naver_cafe.NaverCafeCrawler",
        "example": "https://cafe.naver.com/카페이름",
        "note": "* config.py에 네이버 아이디/비밀번호 입력 필요",
    },
    "2": {
        "name": "네이버 블로그",
        "class": "crawler.naver_blog.NaverBlogCrawler",
        "example": "https://blog.naver.com/블로그아이디",
        "note": "",
    },
    "3": {
        "name": "디시인사이드",
        "class": "crawler.dcinside.DcinsideCrawler",
        "example": "https://gall.dcinside.com/board/lists/?id=갤러리아이디",
        "note": "유저 IP 수집 가능",
    },
    "4": {
        "name": "에펨코리아",
        "class": "crawler.fmkorea.FmkoreaCrawler",
        "example": "https://www.fmkorea.com/best",
        "note": "",
    },
    "5": {
        "name": "루리웹",
        "class": "crawler.ruliweb.RuliwebCrawler",
        "example": "https://bbs.ruliweb.com/community/board/300143",
        "note": "",
    },
    "6": {
        "name": "뽐뿌",
        "class": "crawler.ppomppu.PpomppuCrawler",
        "example": "https://www.ppomppu.co.kr/zboard/zboard.php?id=freeboard",
        "note": "",
    },
    "7": {
        "name": "클리앙",
        "class": "crawler.clien.ClienCrawler",
        "example": "https://www.clien.net/service/board/park",
        "note": "",
    },
}


def print_banner():
    print()
    print("=" * 50)
    print("  Brush - 한국 커뮤니티 웹 크롤러")
    print("=" * 50)
    print()
    print("  * 이 프로그램은 개인 학습/연구 목적으로만")
    print("    사용하세요.")
    print()

    if config.KEYWORDS:
        print("  현재 키워드: " + ", ".join(config.KEYWORDS))
    else:
        print("  현재 키워드: 없음 (모든 게시글 수집)")

    print("  최대 페이지: " + str(config.MAX_PAGES))
    print()


def print_menu():
    print("-" * 50)
    print("  크롤링할 사이트를 선택하세요:")
    print("-" * 50)
    for key, site in SITES.items():
        line = "  " + key + ". " + site["name"]
        if site["note"]:
            line += "  " + site["note"]
        print(line)
    print()
    print("  8. 키워드 변경")
    print("  9. 최대 페이지 수 변경")
    print("  0. 종료")
    print("-" * 50)


def get_crawler(class_path):
    module_path, class_name = class_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    cls = getattr(module, class_name)
    return cls()


def change_keywords():
    print()
    print("  검색할 키워드를 입력하세요.")
    print("  여러 개는 쉼표(,)로 구분합니다.")
    print("  예: 맛집, 추천, 후기")
    print("  비워두고 Enter를 누르면 모든 게시글을 수집합니다.")
    print()
    user_input = input("  키워드: ").strip()

    if user_input:
        config.KEYWORDS = [kw.strip() for kw in user_input.split(",") if kw.strip()]
        print()
        print("  키워드가 설정되었습니다: " + ", ".join(config.KEYWORDS))
    else:
        config.KEYWORDS = []
        print()
        print("  키워드가 비워졌습니다. 모든 게시글을 수집합니다.")


def change_max_pages():
    print()
    print("  현재 최대 페이지 수: " + str(config.MAX_PAGES))
    user_input = input("  새로운 페이지 수 (1~50): ").strip()

    try:
        pages = int(user_input)
        if 1 <= pages <= 50:
            config.MAX_PAGES = pages
            print()
            print("  최대 페이지가 " + str(pages) + "으로 변경되었습니다.")
        else:
            print()
            print("  1에서 50 사이의 숫자를 입력해주세요.")
    except ValueError:
        print()
        print("  숫자를 입력해주세요.")


def run_crawl(site_key):
    site = SITES[site_key]

    print()
    print("  [" + site["name"] + "] 크롤링을 시작합니다.")
    if site["note"]:
        print("  " + site["note"])

    print()
    print("  게시판 주소를 입력하세요.")
    print("  예: " + site["example"])
    print()

    board_url = input("  주소: ").strip()
    if not board_url:
        print("  주소가 입력되지 않았습니다.")
        return

    # 키워드 설정
    if not config.KEYWORDS:
        print()
        print("  키워드가 설정되어 있지 않습니다.")
        kw_input = input("  키워드를 입력하세요 (없으면 Enter): ").strip()
        if kw_input:
            keywords = [kw.strip() for kw in kw_input.split(",") if kw.strip()]
        else:
            keywords = []
    else:
        keywords = config.KEYWORDS

    # 크롤러 생성 및 실행
    try:
        crawler = get_crawler(site["class"])
        results = crawler.crawl(board_url, keywords=keywords, max_pages=config.MAX_PAGES)

        if not results:
            print()
            print("  수집된 게시글이 없습니다.")
            return

        # 엑셀 저장
        filepath = save_to_excel(results, site["name"])

        # 댓글 수 합계
        total_comments = sum(len(p.get("comments", [])) for p in results)

        print()
        print("=" * 50)
        print("  크롤링 완료!")
        print("  게시글: " + str(len(results)) + "개")
        print("  댓글: " + str(total_comments) + "개")
        print("  저장 위치: " + filepath)
        print("=" * 50)

    except Exception as e:
        print()
        print("  [오류] 크롤링 중 문제가 발생했습니다: " + str(e))


def main():
    print_banner()

    while True:
        print_menu()
        choice = input("\n  선택: ").strip()

        if choice == "0":
            print()
            print("  프로그램을 종료합니다. 감사합니다!")
            break
        elif choice == "8":
            change_keywords()
        elif choice == "9":
            change_max_pages()
        elif choice in SITES:
            run_crawl(choice)
        else:
            print()
            print("  올바른 번호를 입력해주세요.")

        print()


if __name__ == "__main__":
    main()
