from django.urls import path

from inspection import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.list_view, name="list"),
    path("inspections/new/", views.create_view, name="create"),
    path("inspections/<int:pk>/", views.detail_view, name="detail"),
    path("bearing/", views.tier_overview_view, name="tier_overview"),
    path("bearing/tier/<int:tier>/", views.tier_members_view, name="tier_members"),
    path("bearing/snapshots/", views.snapshot_list_view, name="snapshot_list"),
    path("bearing/snapshots/<int:pk>/", views.snapshot_detail_view, name="snapshot_detail"),
    path(
        "bearing/snapshots/<int:pk>/tier/<int:tier>/",
        views.snapshot_tier_view,
        name="snapshot_tier",
    ),
    path("bearing/snapshots/issue/", views.snapshot_issue_view, name="snapshot_issue"),
]
