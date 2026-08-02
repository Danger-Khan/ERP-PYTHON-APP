def process_query(data: list[dict], search: str = None, filters: dict = None, 
                  sort_by: str = None, sort_desc: bool = False, 
                  page: int = 1, limit: int = 25) -> dict:
    
    result = data

    # 1. Filters (Exact Match)
    if filters:
        for key, val in filters.items():
            if val:
                result = [row for row in result if str(row.get(key, '')) == str(val)]

    # 2. Live Search (Global Text Match)
    if search:
        search_lower = search.lower()
        result = [
            row for row in result 
            if any(search_lower in str(v).lower() for v in row.values())
        ]

    # 3. Sorting
    if sort_by:
        try:
            # Attempt numeric sort, fallback to string sort
            result.sort(
                key=lambda x: float(x.get(sort_by, 0)) if str(x.get(sort_by, '')).replace('.','',1).isdigit() else str(x.get(sort_by, '')).lower(), 
                reverse=sort_desc
            )
        except Exception:
            pass

    # 4. Pagination
    total = len(result)
    start = (page - 1) * limit
    end = start + limit
    paginated_result = result[start:end]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": paginated_result
    }