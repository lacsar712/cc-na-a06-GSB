from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import (
    BearingSnapshot,
    ClassificationSetting,
    Inspection,
    SnapshotMember,
)
from inspection.rules import BUCKET_NAMES, classify_bucket, judge, valid_bounds


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def _bucket_labels(near_bound: float, far_bound: float) -> list[str]:
    return [
        f"小偏角（|偏差| ≤ {near_bound:g}）",
        f"中偏角（{near_bound:g} < |偏差| ≤ {far_bound:g}）",
        f"大偏角（|偏差| > {far_bound:g}）",
    ]


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
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error})


@login_required
@require_http_methods(["GET", "POST"])
def classification_view(request):
    """现场页：服务端按当前两道档界分三档，给条数、可点进灯号列表；
    持灯账号可在同页改档界或签发快照。"""
    setting = ClassificationSetting.load()

    if request.method == "POST":
        if not _can_write(request.user):
            return HttpResponseForbidden("仅持灯账号可修改档界或签发快照")
        action = request.POST.get("action", "update")
        if action == "issue":
            snapshot = _issue_snapshot(setting, request.user.username)
            return redirect("snapshot_detail", pk=snapshot.pk)
        # 默认动作：更新两道档界
        error = ""
        try:
            near = float(request.POST["near_bound"])
            far = float(request.POST["far_bound"])
        except (KeyError, ValueError):
            error = "两道档界都要填数字"
        else:
            if not valid_bounds(near, far):
                error = "档界需满足 0 ≤ 第一道 ≤ 第二道"
            else:
                setting.near_bound = near
                setting.far_bound = far
                setting.updated_by = request.user.username
                setting.save()
                return redirect("classification")
    else:
        error = ""

    buckets = _live_buckets(setting)
    labels = _bucket_labels(setting.near_bound, setting.far_bound)
    bucket_cards = [
        {"index": i, "name": BUCKET_NAMES[i], "label": labels[i], "count": len(buckets[i])}
        for i in range(3)
    ]
    snapshots = BearingSnapshot.objects.all()
    return render(
        request,
        "classification.html",
        {
            "setting": setting,
            "bucket_cards": bucket_cards,
            "snapshots": snapshots,
            "error": error,
        },
    )


@login_required
def classification_bucket_view(request, bucket: int):
    """点进某一档：服务端按当前档界列出该档灯号。"""
    if bucket not in (0, 1, 2):
        return HttpResponseForbidden("没有这一档")
    setting = ClassificationSetting.load()
    items = [
        (row, abs(row.bearing_error_deg))
        for row in Inspection.objects.all()
        if classify_bucket(row.bearing_error_deg, setting.near_bound, setting.far_bound)
        == bucket
    ]
    return render(
        request,
        "classification_bucket.html",
        {
            "bucket": bucket,
            "bucket_name": BUCKET_NAMES[bucket],
            "label": _bucket_labels(setting.near_bound, setting.far_bound)[bucket],
            "items": items,
        },
    )


@login_required
def snapshot_list_view(request):
    snapshots = BearingSnapshot.objects.all()
    return render(request, "snapshot_list.html", {"snapshots": snapshots})


@login_required
def snapshot_detail_view(request, pk):
    snapshot = get_object_or_404(BearingSnapshot, pk=pk)
    labels = _bucket_labels(snapshot.near_bound, snapshot.far_bound)
    counts = [snapshot.near_count, snapshot.mid_count, snapshot.far_count]
    bucket_cards = [
        {
            "index": i,
            "name": BUCKET_NAMES[i],
            "label": labels[i],
            "count": counts[i],
            "members": list(
                snapshot.members.filter(bucket=i).select_related("inspection")
            ),
        }
        for i in range(3)
    ]
    return render(
        request,
        "snapshot_detail.html",
        {"snapshot": snapshot, "bucket_cards": bucket_cards},
    )


def _live_buckets(setting: ClassificationSetting) -> list[list[Inspection]]:
    groups: list[list[Inspection]] = [[], [], []]
    for row in Inspection.objects.all():
        groups[
            classify_bucket(row.bearing_error_deg, setting.near_bound, setting.far_bound)
        ].append(row)
    return groups


@transaction.atomic
def _issue_snapshot(setting: ClassificationSetting, username: str) -> BearingSnapshot:
    """冻结当时两道档界、每档条数和成员主键。"""
    buckets = _live_buckets(setting)
    snapshot = BearingSnapshot.objects.create(
        near_bound=setting.near_bound,
        far_bound=setting.far_bound,
        near_count=len(buckets[0]),
        mid_count=len(buckets[1]),
        far_count=len(buckets[2]),
        issued_by=username,
    )
    SnapshotMember.objects.bulk_create(
        [
            SnapshotMember(snapshot=snapshot, inspection=row, bucket=bucket)
            for bucket, rows in enumerate(buckets)
            for row in rows
        ]
    )
    return snapshot
