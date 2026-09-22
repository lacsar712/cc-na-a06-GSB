"""方位偏角按绝对值分三档，分档计算只在服务端进行。"""

TIER_LABELS = {0: "小偏角", 1: "中偏角", 2: "大偏角"}


def classify(bearing_error_deg: float, low_bound: float, high_bound: float) -> int:
    """按偏角绝对值归为 0/1/2 三档：|x| < 低档界 为小档，< 高档界 为中档，其余大档。"""
    v = abs(bearing_error_deg)
    if v < low_bound:
        return 0
    if v < high_bound:
        return 1
    return 2


def bucket_rows(rows, low_bound: float, high_bound: float) -> list[dict]:
    """把实测记录分进三档，返回每档标签、条数与成员。"""
    buckets = [
        {"tier": t, "label": TIER_LABELS[t], "count": 0, "rows": []} for t in range(3)
    ]
    for row in rows:
        t = classify(row.bearing_error_deg, low_bound, high_bound)
        buckets[t]["rows"].append(row)
        buckets[t]["count"] += 1
    return buckets
