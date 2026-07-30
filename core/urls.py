from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminPortalView,
    BloodInventoryViewSet,
    DonationAppointmentViewSet,
    EmergencyRequestViewSet,
    BloodBankDashboardView,
    DonorDashboardView,
    HospitalDashboardPageView,
    HospitalDashboardView,
    HospitalInventorySummaryView,
    HospitalProfileViewSet,
    LandingPageView,
    LogoutViewCustom,
    PendingApprovalView,
    RegisterView,
    RoleAwareLoginView,
    RoleRedirectView,
)


router = DefaultRouter()
router.register(r"hospital-profiles", HospitalProfileViewSet, basename="hospitalprofile")
router.register(r"blood-inventory", BloodInventoryViewSet, basename="bloodinventory")
router.register(r"appointments", DonationAppointmentViewSet, basename="appointments")
router.register(r"emergency-requests", EmergencyRequestViewSet, basename="emergencyrequests")

app_name = "core"

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("auth/login/", RoleAwareLoginView.as_view(), name="login"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/logout/", LogoutViewCustom.as_view(), name="logout"),
    path("dashboard/", RoleRedirectView.as_view(), name="dashboard-redirect"),
    path("auth/pending-approval/", PendingApprovalView.as_view(), name="pending-approval"),
    path("donor/dashboard/", DonorDashboardView.as_view(), name="donor-dashboard"),
    path("hospital/dashboard/", HospitalDashboardPageView.as_view(), name="hospital-dashboard-page"),
    path("admin-portal/", AdminPortalView.as_view(), name="admin-portal"),
    path("blood-bank/", BloodBankDashboardView.as_view(), name="blood-bank-dashboard"),
    path("", include(router.urls)),
    path("hospital/dashboard/live/", HospitalDashboardView.as_view(), name="hospital-dashboard"),
    path(
        "hospital/<int:hospital_id>/inventory-summary/",
        HospitalInventorySummaryView.as_view(),
        name="hospital-inventory-summary",
    ),
]
