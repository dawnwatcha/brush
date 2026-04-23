# 2026-04-16 · 초기 구축부터 웹 배포까지

## 📍 이 문서의 목적
프로젝트가 "빈 폴더"에서 "Streamlit Cloud에 배포된 웹 크롤러"가 되기까지 하루 동안 이뤄진 모든 결정과 변경을 기록합니다. 다음 세션에서 이 문서를 먼저 읽으면 context를 빠르게 회복할 수 있도록 씁니다.

---

## 🎯 프로젝트 개요

**이름:** Brush
**목적:** 한국 커뮤니티 사이트에서 특정 키워드가 포함된 게시글과 댓글을 수집하여 엑셀로 정리하는 프로그램.

**대상 사이트 (7개):**
1. 네이버 카페
2. 네이버 블로그
3. 디시인사이드
4. 에펨코리아
5. 루리웹
6. 뽐뿌
7. 클리앙

**수집 항목:** 게시글 제목, 본문, 게시일, 댓글 내용, 댓글 일자, 유저 닉네임, 유저 IP(가능한 곳)

**출력:** 엑셀 파일 (.xlsx, 2개 시트 — "게시글" / "댓글")

**사용자 프로필:** 개발 경험이 없는 초보. 더블클릭으로 실행 가능해야 하고, 모든 설명은 한국어 + 비기술자 눈높이로.

---

## 🏛 아키텍처

### 디렉토리 구조
```
C:\Projects\brush\
├── run.bat                  # (데스크톱) 더블클릭 실행
├── install.bat              # (데스크톱) 더블클릭 설치
├── requirements.txt         # 의존성
├── main.py                  # (데스크톱) CLI 메뉴 진입점
├── app.py                   # (웹) Streamlit 진입점
├── config.py                # 사용자 설정 (키워드, 요청 간격, 네이버 계정)
├── crawler/
│   ├── __init__.py
│   ├── base.py              # BaseCrawler (공통 로직: crawl, 필터링, 검색 분기)
│   ├── clien.py
│   ├── ppomppu.py
│   ├── ruliweb.py
│   ├── fmkorea.py
│   ├── dcinside.py
│   ├── naver_cafe.py        # Selenium (로그인 필요)
│   └── naver_blog.py        # Selenium (iframe 처리)
├── utils/
│   ├── __init__.py
│   ├── http_client.py       # 공유 HTTP 세션, 재시도, 지연, Selenium 팩토리
│   ├── filters.py           # 키워드 매칭
│   └── excel_writer.py      # 엑셀 저장 (2시트)
├── output/                  # 엑셀 결과 (gitignored)
└── docs/worklogs/           # 세션별 작업 기록 (이 파일 포함)
```

### 핵심 추상화
- **BaseCrawler (crawler/base.py)**: `get_post_list`, `search_posts`, `get_post_detail`를 구현하면 `crawl()`이 나머지를 처리.
- **crawl() 흐름**:
  1. 키워드가 있으면 `search_posts` 시도 → 실패(`NotImplementedError`)하면 `get_post_list` + 제목 필터로 폴백.
  2. 여러 키워드면 각각 검색 후 URL 기준 중복 제거.
  3. 각 게시글에 `get_post_detail` 호출 → `utils.filters.matches_keywords`로 본문/댓글까지 재검증.
- **공유 HTTP 세션 (utils/http_client.py)**: `requests.Session`을 싱글톤처럼 사용. 요청 간 최소 지연(`config.REQUEST_DELAY`), 429/500 등 재시도, 403 시 30초 대기 후 1회 재시도. `fetch()`는 BeautifulSoup 반환, `fetch_json()`은 JSON 반환.

---

## 📚 오늘의 커밋 타임라인

```
afd0b16  Initial commit: 한국 커뮤니티 웹 크롤러 Brush
337b8e2  사이트 자체 검색 기능 활용으로 효율성 개선
e3299c5  디시인사이드와 네이버 블로그를 통합검색 기반으로 변경
c368de0  디시인사이드 댓글 JSON 요청 실패 오류 수정
5d36a02  Streamlit 웹 UI 추가 (app.py)
6262a04  Streamlit Cloud 배포 오류 수정
```

### afd0b16 — Initial commit
- 7개 사이트별 크롤러, 공통 구조(base), 유틸(http_client, filters, excel_writer), CLI(main.py), 배치(install.bat, run.bat), config.py 생성.
- `.gitignore`: `__pycache__/`, `output/`, `venv/`, `.vscode/`, `.idea/`, `Thumbs.db`, `.DS_Store`. `config.py`는 **기본값이 비어있으므로 그대로 추적**하고, 네이버 비밀번호 입력 후에는 커밋하지 말라는 주석만 남겨둠.
- Python 3.12.10 사용. `c:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe`. Microsoft Store 스텁이 PATH에 먼저 잡혀 있어 `python --version`이 실패하는 문제 있음 → 절대 경로 사용해 확인.
- 한글 콘솔 출력 대응: `main.py` 상단에서 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`로 강제 UTF-8.

### 337b8e2 — 사이트 자체 검색 기능 활용
- 기존 방식(전체 목록 가져와서 필터)은 느리고 차단 위험. 각 사이트 검색 URL로 바꿔 효율화.
- base.py에 `search_posts()` 추상 메서드 추가, `crawl()`이 키워드 유무로 분기.
- 미구현 사이트는 `NotImplementedError` → 폴백 로직 발동.
- 여러 키워드 입력 시 각각 검색하고 URL 기준 dedupe.

### e3299c5 — DCInside/Naver Blog 통합검색 전환
- **DCInside**: 개별 갤러리 검색 → `search.dcinside.com/post/sort/latest/q/키워드/p/페이지` (전체 사이트).
- **Naver Blog**: 개별 블로그 검색 → `search.naver.com/search.naver?where=blog&query=키워드` (전체 네이버).
- Naver Blog 검색은 `requests`만으로 충분 (Selenium 필요 없음). 단, **상세(`get_post_detail`)는 여전히 Selenium 사용**.
- app.py에는 아직 반영 안 됨 (이 시점엔 main.py만 있었음). main.py에 `global_search` 플래그 추가해 URL을 선택사항으로 처리.

### c368de0 — DCInside 댓글 JSON 요청 실패 수정
- 증상: 모든 게시글에서 `[오류] JSON 요청 실패: Expecting value: line 1 column 1 (char 0)` 출력.
- 원인: 디시 댓글 API(`/board/comment/`)가 응답으로 "정상적인 접근이 아닙니다." 문자열을 돌려줌 → JSON 파싱 실패.
- 근본 원인: `e_s_n_o` 토큰 위치가 바뀜. 예전에는 `<script>` 안 전역 변수였는데, 현재는 `<input type="hidden" name="e_s_n_o" value="...">` 로 페이지에 들어있음.
- 수정:
  1. `crawler/dcinside.py _get_comments`: `soup.select_one("input[name=e_s_n_o]").get("value")`로 추출. 실패 시 스크립트 정규식 폴백.
  2. URL로 갤러리 타입 자동 판별:
     - `/mgallery/` → `_GALLTYPE_=M`
     - `/mini/` → `_GALLTYPE_=MI`
     - `/person/` → `_GALLTYPE_=P`
     - 그 외 → `_GALLTYPE_=G`
  3. `Origin: https://gall.dcinside.com` 헤더 추가.
  4. `utils/http_client.py fetch_json`: JSON이 아닌 응답(`{` 또는 `[`로 시작 안 하면)은 조용히 `None` 반환. 더 이상 스택트레이스 노이즈 없음.

### 5d36a02 — Streamlit 웹 UI 추가
- `app.py`: Streamlit 기반 웹 UI. 사이드바에서 사이트/키워드/URL/페이지 설정, `st.status`로 진행상태, 결과 테이블(`st.dataframe`), `st.expander`로 각 게시글 상세, `st.download_button`으로 엑셀 바이너리 다운로드.
- **중요 제약:** 이 커밋 기준 app.py는 `crawler.naver_blog`까지 포함. 하지만 `naver_blog.get_post_detail`이 Selenium을 쓰므로 Cloud 환경에서는 깨짐 — 다음 커밋(6262a04)에서 제외됨.
- `build_excel_bytes()`는 `utils/excel_writer.save_to_excel()`과 거의 같은 로직을 `BytesIO`로 리턴하도록 재작성 (파일 디스크 저장 없이 메모리에서 다운로드 스트림 생성).

### 6262a04 — Streamlit Cloud 배포 오류 수정
- 증상: Streamlit Cloud에서 "Error installing requirements".
- 원인 2가지:
  1. `selenium==4.18.1` — Cloud 환경에 Chrome이 없어 런타임 시점 문제도 있지만, 설치 의존성(특히 `trio`, `urllib3`)이 최신 Python/pandas와 충돌 가능.
  2. `pandas==3.0.2` — 로컬에 깔린 릴리스 후보 버전을 그대로 핀했음. Cloud에서 해당 버전 wheel이 없어 실패.
- 수정:
  - `requirements.txt`: `selenium` 제거, 모든 핀을 `>=`로 완화.
  - `app.py`: `crawler.naver_blog` import 및 SITES dict에서 "네이버 블로그" 제거. Cloud에서 사용 가능한 5개 사이트만(클리앙/뽐뿌/루리웹/에펨코리아/디시인사이드) 남김.

---

## 🌐 배포 정보

- **GitHub**: https://github.com/dawnwatcha/brush (public)
- **Streamlit Cloud**: 배포 성공 (데모 직전 완료). URL은 사용자가 설정한 subdomain.
- **기본 브랜치**: `main` (초기 `master`였다가 GitHub 푸시 전 `git branch -M main`으로 변경)
- **Git 사용자**: `dawn <dawn@watcha.com>` (global config)
- **인증**: Git Credential Manager (Windows 기본). PAT/SSH 별도 설정 없이 push 성공.

---

## 🧠 주요 설계 결정

1. **사이트별 파일 분리**: 각 사이트의 HTML/API가 완전히 달라서 공통 파싱 로직을 강제하지 않음. BaseCrawler는 흐름만 정의, 파싱은 전적으로 하위 클래스.
2. **requests + BeautifulSoup 기본, Selenium은 최후**: Selenium은 네이버 카페(로그인)와 네이버 블로그 상세(iframe)에만 사용. 나머지는 순수 HTTP로. Selenium은 `utils.http_client.get_selenium_driver()`에 격리.
3. **키워드 필터링 2단계**:
   - 1단계: `search_posts`에서 사이트 검색 결과로 1차 필터 (또는 `get_post_list` 결과의 제목 문자열 매칭).
   - 2단계: `get_post_detail` 후 본문+댓글까지 모두 검사해 재필터. 사이트 검색이 부정확할 때 대비.
4. **엑셀 2시트 구조**: 1:N(게시글:댓글)을 한 시트에 평탄화하면 같은 게시글이 여러 행으로 반복되어 혼란. "게시글" / "댓글" 2시트를 URL을 조인 키로 연결.
5. **요청 간격 전역 제어**: `utils.http_client._last_request_time`로 모든 요청 사이에 `config.REQUEST_DELAY`(기본 2초, 디시는 3초) 강제 대기. 개별 크롤러에서 지연 관리할 필요 없음.
6. **통합검색 사이트는 URL 선택사항**: main.py/app.py에서 `global_search=True`인 사이트는 board_url 없이 키워드만으로 동작.

---

## ⚠️ 알려진 이슈 / 미해결

1. **Streamlit Cloud에서 네이버 카페/블로그 사용 불가** ← **다음 세션에서 해결 중** (아래 "진행 중인 작업" 참고)
2. **pandas 3.x 의존**: 로컬에 우연히 깔렸을 뿐, `requirements.txt`는 `>=2.2.0`이라 Cloud는 2.x가 설치됨. 코드상 2.x/3.x 모두 호환되는 API만 사용 중이라 문제 없음.
3. **LF/CRLF 경고**: Windows에서 git add 시 매번 뜨는데 무해. 필요하면 `.gitattributes`로 강제할 수 있지만 현재는 방치.
4. **네이버 카페 로그인 경로 미검증**: `crawler/naver_cafe.py`가 JavaScript 인젝션으로 로그인을 시도하는데, 캡차가 뜨거나 2FA가 걸린 계정에서는 실패할 수 있음. 데모에서 실제 로그인은 해본 적 없음.
5. **디시인사이드 댓글 페이지 제한**: 최대 5페이지까지만 가져옴(`for page in range(1, 6)`). 수십 페이지짜리 글은 일부 누락 가능.
6. **Ruliweb 통합검색 URL 미확인**: `https://bbs.ruliweb.com/search?q=` 은 "결과 없음" 응답. 올바른 URL 패턴 필요 (`ajax/search/list` 등 탐색 필요).

---

## 🔧 진행 중인 작업 (미완료) — 다음 세션에서 이어서 할 것

사용자 마지막 요청: **"네이버 카페랑 블로그를 선택할 수 없는 점 해결해줘. 나머지 사이트들도 다 통합검색으로 바꿔주고"**

### 목표
1. 네이버 카페와 네이버 블로그를 **Streamlit Cloud(Selenium 없음) 환경에서도 동작**하게.
2. 현재 "게시판별 검색"인 4개 사이트(클리앙/뽐뿌/루리웹/에펨코리아)를 **사이트 전체 통합검색** 방식으로 전환. 사용자는 게시판 URL 입력 없이 키워드만 주면 됨.

### 이미 확인한 URL 패턴 (이 시점까지 테스트 완료)
| 사이트 | 통합검색 URL | 확인 상태 |
|---|---|---|
| 클리앙 | `https://www.clien.net/service/search?q={kw}&sort=recency` | ✅ 18개 결과 확인 |
| 뽐뿌 | `https://www.ppomppu.co.kr/search_bbs.php?search_type=sub_memo&keyword={kw}` | ✅ 32개 고유 URL |
| 루리웹 | `https://bbs.ruliweb.com/search?q={kw}` | ❌ "결과 없음" — URL 재탐색 필요 |
| 에펨코리아 | 미확인 | ❌ `https://www.fmkorea.com/search.php?keyword=...` 등 시도 필요 |
| 디시인사이드 | `https://search.dcinside.com/post/sort/latest/q/{kw}/p/{page}` | ✅ 이미 적용됨 |
| 네이버 블로그 | `https://search.naver.com/search.naver?where=blog&query={kw}&start={N}` | ✅ 이미 적용됨 (검색만) |
| 네이버 카페 | `https://search.naver.com/search.naver?where=article&query={kw}` 또는 cafe 전용 엔드포인트 | ❌ 탐색 필요 |

### 기술적 장벽
- **네이버 블로그 상세 (Selenium 의존)**: `crawler/naver_blog.py get_post_detail`가 Selenium으로 iframe(`mainFrame`)을 전환해 본문 추출. 해결 방법: `https://blog.naver.com/PostView.naver?blogId={id}&logNo={no}`를 `requests`로 직접 fetch하면 iframe 없이 본문 접근 가능 — 이 URL 패턴으로 재작성 필요.
- **네이버 카페 전반 (로그인 의존)**: 카페 글 본문은 로그인 없이 접근 불가가 일반적. 대안은 네이버 통합검색 결과의 snippet을 "본문"으로 사용하는 제한적 구현. 또는 네이버 카페 공개 글에 한해 `https://cafe.naver.com/CafeId/ArticleId`를 `requests`로 fetch 시도. 데모 전에는 "검색 결과 snippet을 본문으로 표시"하는 간이 방식이 현실적.

### 계획한 변경 파일 (아직 건드리지 않음)
- `crawler/clien.py` — `search_posts`에서 `boardCd` 파라미터 제거, `board_url` 무시
- `crawler/ppomppu.py` — `search_posts`에서 `bbs_cate` 파라미터 제거
- `crawler/ruliweb.py` — 통합검색 URL 새로 탐색 후 적용
- `crawler/fmkorea.py` — 통합검색 URL 새로 탐색 후 적용
- `crawler/naver_blog.py` — `get_post_detail`을 `PostView.naver` requests 기반으로 재작성
- `crawler/naver_cafe.py` — Naver 통합검색 article 탭 기반으로 전체 재작성 (또는 주석 처리 후 별도 클래스 신설)
- `app.py` — 네이버 카페/블로그 SITES에 복원, 모든 사이트 `global_search=True`로 설정해 URL 입력란 제거
- `main.py` — 동일하게 URL을 선택사항으로 통일

### 현재 작업 중이던 마지막 지점
- 각 사이트 통합검색 URL 패턴을 `curl`/`fetch`로 탐색하던 중
- 루리웹 / FM코리아 URL이 아직 확인 안 됨
- 확인 완료 후 code change 돌입 예정이었음

---

## 🧪 로컬 실행/테스트 방법

### CLI 버전 (main.py)
```bash
cd C:\Projects\brush
python main.py
# 메뉴에서 사이트 번호 선택 → URL(또는 빈칸) → 키워드
```

### 웹 버전 (app.py)
```bash
cd C:\Projects\brush
python -m streamlit run app.py
# 브라우저에서 http://localhost:8501 자동 열림
```

### 개별 크롤러 테스트
```python
# 예: 클리앙 통합 흐름 테스트
from crawler.clien import ClienCrawler
c = ClienCrawler()
results = c.crawl("https://www.clien.net/service/board/park", keywords=["맛집"], max_pages=1)
# -> 17개 수집 (실측)
```

### 개별 사이트 검색 URL 점검 스니펫
`utils.http_client.fetch(url, delay=0)`로 빠르게 응답 구조 확인. 스크립트는 Bash heredoc으로 작성하고 `python < <<EOF` 로 실행. stdout에 한글이 깨지면 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` 첫 줄에 추가.

---

## 🧷 다음 세션 진입 시 체크리스트

1. 이 문서를 먼저 읽는다.
2. `git log --oneline`으로 현재 커밋 상태 확인. (마지막 커밋: `6262a04 Streamlit Cloud 배포 오류 수정`)
3. `git status`로 working tree 확인. (이 문서 커밋 직후라면 clean)
4. **진행 중인 작업** 섹션을 열어 "현재 작업 중이던 마지막 지점"부터 재개.
5. 통합검색 URL 탐색 먼저: 루리웹, FM코리아. `curl -s 'URL' | head -200` 또는 위 스니펫으로.
6. URL 확정되면 해당 크롤러 `search_posts` 수정 → 로컬 테스트 → 모든 사이트 끝나면 `app.py` 업데이트 → 커밋 → push → Streamlit Cloud 자동 재배포.

---

## 📎 참고: 유용했던 스니펫 & 디버깅 메모

### 한글 stdout 강제
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

### BS4로 특정 속성 있는 input 찾기
```python
soup.select_one("input[name=e_s_n_o]").get("value", "")
```

### 네이버 검색 결과에서 블로그 URL 추출 (class가 동적으로 생성되어 정규식 사용)
```python
import re
pattern = re.compile(r"^https://blog\.naver\.com/[^/?#]+/\d+")
for link in soup.select("a[href]"):
    m = pattern.match(link.get("href", ""))
    if m:
        url = m.group()
        title = link.get_text(strip=True)  # 빈 링크(썸네일)는 제외, 가장 긴 텍스트 채택
```

### 디시 댓글 API 요청 형식 (검증 완료)
```python
POST https://gall.dcinside.com/board/comment/
Headers:
  Referer: <post_url>
  Origin: https://gall.dcinside.com
  X-Requested-With: XMLHttpRequest
Form:
  id=<gallery_id>
  no=<post_no>
  cmt_id=<gallery_id>
  cmt_no=<post_no>
  comment_page=<n>
  e_s_n_o=<hidden input value>
  _GALLTYPE_=<G|M|MI|P>
```

### Streamlit Cloud 배포 체크
- `requirements.txt`는 Cloud의 Python에서 설치 가능한 버전이어야 함. `>=` 권장.
- Chrome/Selenium 전제로 하는 코드는 에러 발생 → 해당 사이트 기능 분리 또는 Selenium 의존 제거.

---

## 🤝 사용자 컨텍스트 (관계 설정용)
- 개발 경험 없음. 초보자 눈높이 설명 필수. 답변은 항상 한국어.
- 빠른 의사결정 선호 — 필요 시 선택지 간결하게 제시.
- 깊이 파고들기보다 "돌아가게" 먼저 만드는 스타일에 긍정적.
- Windows 11 / VSCode / Git 2.53 / Python 3.12.10 환경.
- 데모를 앞두고 "20분 뒤에 데모해야 한다"며 압박 있던 순간 있었음. 실용적 타협 지향.
