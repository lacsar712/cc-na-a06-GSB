import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inspection", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassificationSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("near_bound", models.FloatField(default=0.5, verbose_name="小偏角/中偏角档界")),
                ("far_bound", models.FloatField(default=2.0, verbose_name="中偏角/大偏角档界")),
                ("updated_by", models.CharField(blank=True, max_length=64, verbose_name="最后修改人")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "方位分档设置",
                "verbose_name_plural": "方位分档设置",
            },
        ),
        migrations.CreateModel(
            name="BearingSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("near_bound", models.FloatField(verbose_name="小偏角/中偏角档界")),
                ("far_bound", models.FloatField(verbose_name="中偏角/大偏角档界")),
                ("near_count", models.PositiveIntegerField(verbose_name="小偏角档条数")),
                ("mid_count", models.PositiveIntegerField(verbose_name="中偏角档条数")),
                ("far_count", models.PositiveIntegerField(verbose_name="大偏角档条数")),
                ("issued_by", models.CharField(max_length=64, verbose_name="签发人")),
                ("issued_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-id"],
            },
        ),
        migrations.CreateModel(
            name="SnapshotMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bucket", models.PositiveSmallIntegerField(verbose_name="所属档")),
                (
                    "inspection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="inspection.inspection",
                    ),
                ),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="inspection.bearingsnapshot",
                    ),
                ),
            ],
            options={
                "ordering": ["bucket", "id"],
                "unique_together": {("snapshot", "inspection")},
            },
        ),
    ]
