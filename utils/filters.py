def matches_keywords(post, keywords):
    """게시글(제목, 본문, 댓글)에 키워드가 포함되어 있는지 확인합니다.

    keywords가 비어있으면 항상 True를 반환합니다 (전체 수집 모드).
    """
    if not keywords:
        return True

    # 검색 대상 텍스트를 모두 소문자로 변환하여 비교
    searchable = []
    searchable.append(post.get("title", "").lower())
    searchable.append(post.get("content", "").lower())

    for comment in post.get("comments", []):
        searchable.append(comment.get("content", "").lower())

    combined = " ".join(searchable)

    return any(kw.lower() in combined for kw in keywords)
