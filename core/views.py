from django.db import transaction
from django.db.models import F
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BloodInventory, DonationAppointment, EmergencyRequest, HospitalProfile
from .forms import EmailAuthenticationForm, RegistrationForm
from .forms import BloodRequestForm, DonationAppointmentForm
from .serializers import (
    BloodInventorySerializer,
    DonationAppointmentSerializer,
    EmergencyRequestSerializer,
    HospitalProfileSerializer,
)


class IsHospitalStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or (user.role == "hospital" and user.is_approved))
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and (user.role == "admin" or user.is_superuser))


class HospitalProfileViewSet(viewsets.ModelViewSet):
    queryset = HospitalProfile.objects.select_related("user").all()
    serializer_class = HospitalProfileSerializer
    permission_classes = [IsAdminOrReadOnly]


class BloodInventoryViewSet(viewsets.ModelViewSet):
    queryset = BloodInventory.objects.select_related("hospital", "hospital__user").all()
    serializer_class = BloodInventorySerializer
    permission_classes = [IsHospitalStaff]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        hospital_profile = getattr(user, "hospital_profile", None)
        if hospital_profile:
            return queryset.filter(hospital=hospital_profile)
        return queryset.none()

    def perform_create(self, serializer):
        hospital_profile = getattr(self.request.user, "hospital_profile", None)
        if hospital_profile and not self.request.user.is_superuser:
            serializer.save(hospital=hospital_profile)
        else:
            serializer.save()


class DonationAppointmentViewSet(viewsets.ModelViewSet):
    queryset = DonationAppointment.objects.select_related("donor", "hospital").all()
    serializer_class = DonationAppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmergencyRequestViewSet(viewsets.ModelViewSet):
    queryset = EmergencyRequest.objects.select_related("requester", "hospital").all()
    serializer_class = EmergencyRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"], permission_classes=[IsHospitalStaff])
    def approve(self, request, pk=None):
        emergency_request = self.get_object()
        emergency_request.status = EmergencyRequest.Status.APPROVED
        emergency_request.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(emergency_request).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHospitalStaff])
    def complete(self, request, pk=None):
        emergency_request = self.get_object()

        if emergency_request.status == EmergencyRequest.Status.COMPLETED:
            return Response(self.get_serializer(emergency_request).data)

        with transaction.atomic():
            inventory = (
                BloodInventory.objects.select_for_update()
                .filter(hospital=emergency_request.hospital, blood_group=emergency_request.blood_group)
                .first()
            )
            if inventory is None:
                return Response(
                    {"detail": "Matching inventory item was not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if inventory.units_available < emergency_request.units_required:
                return Response(
                    {"detail": "Not enough units available to complete the request."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            inventory.units_available = F("units_available") - emergency_request.units_required
            inventory.save(update_fields=["units_available", "updated_at"])
            inventory.refresh_from_db(fields=["units_available"])

            emergency_request.fulfilled_units = emergency_request.units_required
            emergency_request.status = EmergencyRequest.Status.COMPLETED
            emergency_request.save(update_fields=["fulfilled_units", "status", "updated_at"])

        return Response(self.get_serializer(emergency_request).data)


class HospitalDashboardView(TemplateView):
    template_name = "core/dashboard.html"


class HospitalInventorySummaryView(APIView):
    permission_classes = [IsHospitalStaff]

    def get(self, request, hospital_id):
        if not request.user.is_superuser:
            hospital_profile = getattr(request.user, "hospital_profile", None)
            if not hospital_profile or hospital_profile.id != hospital_id:
                return Response({"detail": "You can only view your own hospital inventory."}, status=status.HTTP_403_FORBIDDEN)
        inventory = (
            BloodInventory.objects.filter(hospital_id=hospital_id)
            .values("blood_group")
            .annotate(total_units=Sum("units_available"))
            .order_by("blood_group")
        )
        return Response(
            {
                "hospital_id": hospital_id,
                "inventory": list(inventory),
            }
        )


class LandingPageView(TemplateView):
    template_name = "core/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["hospital_count"] = HospitalProfile.objects.count()
        context["inventory_count"] = BloodInventory.objects.count()
        context["request_count"] = EmergencyRequest.objects.count()
        return context


class RoleRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role == "donor":
            return redirect("core:donor-dashboard")
        if user.role == "hospital":
            if user.is_approved:
                return redirect("core:hospital-dashboard-page")
            return redirect("core:pending-approval")
        if user.role == "admin" or user.is_superuser:
            return redirect("core:admin-portal")
        return redirect("core:landing")


class RoleAwareLoginView(LoginView):
    template_name = "core/auth/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.role == "donor":
            return reverse_lazy("core:donor-dashboard")
        if user.role == "hospital":
            if user.is_approved:
                return reverse_lazy("core:hospital-dashboard-page")
            return reverse_lazy("core:pending-approval")
        if user.role == "admin" or user.is_superuser:
            return reverse_lazy("core:admin-portal")
        return reverse_lazy("core:landing")


class RegisterView(FormView):
    template_name = "core/auth/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("core:login")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Your account has been created successfully.")
        if user.role == "donor":
            return redirect("core:donor-dashboard")
        if user.role == "hospital":
            return redirect("core:pending-approval")
        if user.role == "admin" or user.is_superuser:
            return redirect("core:admin-portal")
        return redirect("core:landing")


class LogoutViewCustom(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("core:landing")


class PendingApprovalView(LoginRequiredMixin, TemplateView):
    template_name = "core/pending_approval.html"


class DonorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/donor/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != "donor":
            return redirect("core:login")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["donation_form"] = DonationAppointmentForm()
        context["blood_request_form"] = BloodRequestForm()
        context["appointments"] = DonationAppointment.objects.filter(donor=self.request.user).order_by("-created_at")[:10]
        context["blood_requests"] = EmergencyRequest.objects.filter(requester=self.request.user).order_by("-created_at")[:10]
        context["hospitals"] = HospitalProfile.objects.all().order_by("hospital_name")
        return context

    def post(self, request, *args, **kwargs):
        if request.user.role != "donor":
            return redirect("core:login")

        action = request.POST.get("action")
        if action == "donation":
            form = DonationAppointmentForm(request.POST)
            if form.is_valid():
                appointment = form.save(commit=False)
                appointment.donor = request.user
                appointment.save()
                messages.success(request, "Your donation request has been submitted.")
                return redirect("core:donor-dashboard")
            context = self.get_context_data()
            context["donation_form"] = form
            return self.render_to_response(context)

        if action == "blood_request":
            form = BloodRequestForm(request.POST)
            if form.is_valid():
                blood_request = form.save(commit=False)
                blood_request.requester = request.user
                blood_request.save()
                messages.success(request, "Your blood request has been submitted.")
                return redirect("core:donor-dashboard")
            context = self.get_context_data()
            context["blood_request_form"] = form
            return self.render_to_response(context)

        return redirect("core:donor-dashboard")


class HospitalDashboardPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "core/hospital/dashboard.html"

    def test_func(self):
        user = self.request.user
        return user.is_superuser or (user.role == "hospital" and user.is_approved)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_profile = getattr(self.request.user, "hospital_profile", None)
        if hospital_profile:
            inventory = BloodInventory.objects.filter(hospital=hospital_profile).order_by("blood_group")
            context["hospital_profile"] = hospital_profile
            context["inventory"] = inventory
            context["requests"] = EmergencyRequest.objects.filter(hospital=hospital_profile).order_by("-created_at")[:10]
            context["appointments"] = DonationAppointment.objects.filter(hospital=hospital_profile).order_by(
                "-appointment_datetime"
            )[:10]
        return context


class AdminPortalView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "core/admin/portal.html"

    def test_func(self):
        return self.request.user.role == "admin" or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["hospital_count"] = HospitalProfile.objects.count()
        context["pending_hospital_count"] = HospitalProfile.objects.filter(user__is_approved=False).count()
        context["request_count"] = EmergencyRequest.objects.count()
        context["appointment_count"] = DonationAppointment.objects.count()
        return context


class BloodBankDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "core/blood_bank/dashboard.html"

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.role == "admin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inventory_rows = (
            BloodInventory.objects.select_related("hospital")
            .values("blood_group")
            .annotate(total_units=Sum("units_available"))
            .order_by("blood_group")
        )
        inventory_rows = list(inventory_rows)
        total_units = sum(row["total_units"] for row in inventory_rows)
        palette = ["#dc2626", "#991b1b", "#ef4444", "#b91c1c", "#7f1d1d", "#f87171", "#fecaca", "#fee2e2"]
        slices = []
        legend = []
        cumulative = 0.0
        for index, row in enumerate(inventory_rows):
            units = row["total_units"] or 0
            percent = (units / total_units * 100) if total_units else 0
            start = cumulative
            end = cumulative + percent
            cumulative = end
            color = palette[index % len(palette)]
            slices.append(f"{color} {start:.2f}% {end:.2f}%")
            legend.append(
                {
                    "blood_group": row["blood_group"],
                    "total_units": units,
                    "percent": round(percent, 1),
                    "color": color,
                }
            )

        hospitals = (
            HospitalProfile.objects.select_related("user")
            .annotate(total_units=Sum("inventory_items__units_available"))
            .order_by("-total_units", "hospital_name")
        )

        context["inventory_rows"] = inventory_rows
        context["total_units"] = total_units
        context["chart_slices"] = ", ".join(slices) if slices else "#d4d4d8 0% 100%"
        context["legend_items"] = legend
        context["hospital_cards"] = hospitals
        context["hospital_count"] = HospitalProfile.objects.count()
        context["inventory_count"] = BloodInventory.objects.count()
        context["request_count"] = EmergencyRequest.objects.count()
        return context
