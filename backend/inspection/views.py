from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import (
    BearingSnapshot,
    BearingSnapshotMember,
    BearingSnapshotTier,
    BearingTierSetting,
    Inspection,
)
from inspection.rules import judge
from inspection.tiers import TIER_LABELS, bucket_rows, classify


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def health(_request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "service": "nav-aid-inspection"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    from django.contrib.auth import authenticate, login

    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "用户名或密码错误"
        else:
            login(request, user)
            return redirect("list")
    return render(request, "login.html", {"error": error})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return redirect("login")


@login_required
def list_view(request):
    rows = Inspection.objects.all()
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    return render(request, "detail.html", {"row": row})


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required_cd,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error})


# ---------- 方位分档 ----------


def _parse_bounds(post) -> tuple[float, float] | None:
    try:
        low = float(post["low_bound"])
        high = float(post["high_bound"])
    except (KeyError, ValueError, TypeError):
        return None
    if low < 0 or high <= low:
        return None
    return low, high


@login_required
def tier_overview_view(request):
    """现场页：按当前两道档界服务端分档，给出每档条数，可点进灯号列表。"""
    setting = BearingTierSetting.load()
    error = ""
    if request.method == "POST":
        if not _can_write(request.user):
            return HttpResponseForbidden("仅持灯账号可修改档界")
        parsed = _parse_bounds(request.POST)
        if parsed is None:
            error = "档界需为非负数，且第二道须大于第一道"
        else:
            setting.low_bound, setting.high_bound = parsed
            setting.updated_by = request.user.username
            setting.save(update_fields=["low_bound", "high_bound", "updated_by", "updated_at"])
            return redirect("tier_overview")
    buckets = bucket_rows(
        Inspection.objects.all(), setting.low_bound, setting.high_bound
    )
    snapshots = BearingSnapshot.objects.all()[:10]
    return render(
        request,
        "bearing/overview.html",
        {
            "setting": setting,
            "buckets": buckets,
            "snapshots": snapshots,
            "error": error,
            "can_write": _can_write(request.user),
        },
    )


@login_required
def tier_members_view(request, tier: int):
    if tier not in TIER_LABELS:
        return redirect("tier_overview")
    setting = BearingTierSetting.load()
    rows = [
        r
        for r in Inspection.objects.all()
        if classify(r.bearing_error_deg, setting.low_bound, setting.high_bound) == tier
    ]
    return render(
        request,
        "bearing/tier_members.html",
        {
            "tier": tier,
            "label": TIER_LABELS[tier],
            "low_bound": setting.low_bound,
            "high_bound": setting.high_bound,
            "rows": rows,
            "frozen": False,
        },
    )


@login_required
@require_http_methods(["POST"])
def snapshot_issue_view(request):
    """签发快照：冻结当时两道档界、每档条数和成员主键。"""
    if not _can_write(request.user):
        return HttpResponseForbidden("仅持灯账号可签发分档快照")
    setting = BearingTierSetting.load()
    note = request.POST.get("note", "").strip()[:200]
    with transaction.atomic():
        snapshot = BearingSnapshot.objects.create(
            low_bound=setting.low_bound,
            high_bound=setting.high_bound,
            issued_by=request.user.username,
            note=note,
        )
        buckets = bucket_rows(
            Inspection.objects.all(), setting.low_bound, setting.high_bound
        )
        for bucket in buckets:
            tier_row = BearingSnapshotTier.objects.create(
                snapshot=snapshot,
                tier=bucket["tier"],
                label=bucket["label"],
                count=bucket["count"],
            )
            BearingSnapshotMember.objects.bulk_create(
                [
                    BearingSnapshotMember(
                        tier_row=tier_row,
                        inspection_id=r.pk,
                        aid_code=r.aid_code,
                        bearing_error_deg=r.bearing_error_deg,
                    )
                    for r in bucket["rows"]
                ]
            )
    return redirect("snapshot_detail", pk=snapshot.pk)


@login_required
def snapshot_list_view(request):
    return render(
        request,
        "bearing/snapshot_list.html",
        {"snapshots": BearingSnapshot.objects.all()},
    )


@login_required
def snapshot_detail_view(request, pk):
    snapshot = get_object_or_404(BearingSnapshot, pk=pk)
    return render(request, "bearing/snapshot_detail.html", {"snapshot": snapshot})


@login_required
def snapshot_tier_view(request, pk, tier: int):
    snapshot = get_object_or_404(BearingSnapshot, pk=pk)
    tier_row = get_object_or_404(BearingSnapshotTier, snapshot=snapshot, tier=tier)
    return render(
        request,
        "bearing/tier_members.html",
        {
            "snapshot": snapshot,
            "tier": tier,
            "label": tier_row.label,
            "count": tier_row.count,
            "rows": tier_row.members.all(),
            "frozen": True,
        },
    )
