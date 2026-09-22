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


class ClassificationSetting(models.Model):
    """方位分档的两道档界，全站单例；只允许持灯账号修改。"""

    near_bound = models.FloatField("小偏角/中偏角档界", default=0.5)
    far_bound = models.FloatField("中偏角/大偏角档界", default=2.0)
    updated_by = models.CharField("最后修改人", max_length=64, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "方位分档设置"
        verbose_name_plural = "方位分档设置"

    @classmethod
    def load(cls) -> "ClassificationSetting":
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    def bucket_for(self, bearing_error_deg: float) -> int:
        v = abs(bearing_error_deg)
        if v <= self.near_bound:
            return 0
        if v <= self.far_bound:
            return 1
        return 2


class BearingSnapshot(models.Model):
    """一次签发的分档快照：档界与三档条数在签发时冻结。"""

    near_bound = models.FloatField("小偏角/中偏角档界")
    far_bound = models.FloatField("中偏角/大偏角档界")
    near_count = models.PositiveIntegerField("小偏角档条数")
    mid_count = models.PositiveIntegerField("中偏角档条数")
    far_count = models.PositiveIntegerField("大偏角档条数")
    issued_by = models.CharField("签发人", max_length=64)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    @property
    def total_count(self) -> int:
        return self.near_count + self.mid_count + self.far_count

    def bucket_label(self, bucket: int) -> str:
        if bucket == 0:
            return f"小偏角（|偏差| ≤ {self.near_bound:g}）"
        if bucket == 1:
            return f"中偏角（{self.near_bound:g} < |偏差| ≤ {self.far_bound:g}）"
        return f"大偏角（|偏差| > {self.far_bound:g}）"


class SnapshotMember(models.Model):
    """快照成员：只冻结成员主键和所属档，不复制其余字段。"""

    snapshot = models.ForeignKey(
        BearingSnapshot, on_delete=models.CASCADE, related_name="members"
    )
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE)
    bucket = models.PositiveSmallIntegerField("所属档")

    class Meta:
        ordering = ["bucket", "id"]
        unique_together = [("snapshot", "inspection")]
