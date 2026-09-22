from django.db import models


class Inspection(models.Model):
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    created_by = models.CharField("登记人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    @property
    def abs_bearing(self) -> float:
        return abs(self.bearing_error_deg)


class BearingTierSetting(models.Model):
    """方位偏角分档的两道档界（按偏角绝对值）。全表只有一行。"""

    low_bound = models.FloatField("小/中档界", default=0.5)
    high_bound = models.FloatField("中/大档界", default=2.0)
    updated_by = models.CharField("最后修改人", max_length=64, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "方位分档档界"

    def __str__(self):
        return f"档界 {self.low_bound} / {self.high_bound}"

    @classmethod
    def load(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(low_bound=0.5, high_bound=2.0)
        return obj


class BearingSnapshot(models.Model):
    """签发即冻结的一份分档快照：档界、每档条数、成员主键都不再随后续修改变化。"""

    low_bound = models.FloatField("小/中档界")
    high_bound = models.FloatField("中/大档界")
    issued_by = models.CharField("签发人", max_length=64)
    issued_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField("附注", max_length=200, blank=True, default="")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"方位分档快照 #{self.pk}"


class BearingSnapshotTier(models.Model):
    snapshot = models.ForeignKey(
        BearingSnapshot, on_delete=models.CASCADE, related_name="tiers"
    )
    tier = models.PositiveSmallIntegerField("档位", choices=[(0, "小偏角"), (1, "中偏角"), (2, "大偏角")])
    label = models.CharField("档名", max_length=20)
    count = models.PositiveIntegerField("条数")

    class Meta:
        ordering = ["tier"]
        unique_together = ("snapshot", "tier")


class BearingSnapshotMember(models.Model):
    tier_row = models.ForeignKey(
        BearingSnapshotTier, on_delete=models.CASCADE, related_name="members"
    )
    inspection_id = models.BigIntegerField("实测记录主键")
    aid_code = models.CharField("航标编号", max_length=40)
    bearing_error_deg = models.FloatField("方位偏差")

    class Meta:
        ordering = ["id"]

    @property
    def abs_bearing(self) -> float:
        return abs(self.bearing_error_deg)
