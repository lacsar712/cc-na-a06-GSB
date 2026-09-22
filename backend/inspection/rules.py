BUCKET_NAMES = ("小偏角", "中偏角", "大偏角")


def judge(measured_cd: float, required_cd: float, bearing_error_deg: float) -> tuple[str, str]:
    if measured_cd < required_cd:
        return "不合格", "光强不足"
    if abs(bearing_error_deg) > 2:
        return "不合格", "方位偏差过大"
    return "合格", "光强与方位均在限内"


def classify_bucket(bearing_error_deg: float, near_bound: float, far_bound: float) -> int:
    """按偏角绝对值分三档：0 小、1 中、2 大；档界本身归入较低档。"""
    value = abs(bearing_error_deg)
    if value <= near_bound:
        return 0
    if value <= far_bound:
        return 1
    return 2


def valid_bounds(near_bound: float, far_bound: float) -> bool:
    return near_bound >= 0 and far_bound >= near_bound
