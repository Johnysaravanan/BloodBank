from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import BloodInventory, DonationAppointment, EmergencyRequest, HospitalProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "is_approved", "is_staff", "is_active")
    list_filter = ("role", "is_approved", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name", "phone_number")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone_number")}),
        ("Access", {"fields": ("role", "is_approved", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "phone_number", "role", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")


@admin.register(HospitalProfile)
class HospitalProfileAdmin(admin.ModelAdmin):
    list_display = ("hospital_name", "user", "city", "state", "created_at")
    search_fields = ("hospital_name", "user__email", "city", "state")
    list_filter = ("state", "city")


@admin.register(BloodInventory)
class BloodInventoryAdmin(admin.ModelAdmin):
    list_display = ("hospital", "blood_group", "units_available", "updated_at")
    list_filter = ("blood_group", "hospital")
    search_fields = ("hospital__hospital_name",)


@admin.register(DonationAppointment)
class DonationAppointmentAdmin(admin.ModelAdmin):
    list_display = ("donor", "hospital", "appointment_datetime", "eligibility_status")
    list_filter = ("eligibility_status", "hospital")
    search_fields = ("donor__email", "hospital__hospital_name")


@admin.register(EmergencyRequest)
class EmergencyRequestAdmin(admin.ModelAdmin):
    list_display = ("requester", "hospital", "blood_group", "units_required", "status", "created_at")
    list_filter = ("status", "blood_group", "hospital")
    search_fields = ("requester__email", "hospital__hospital_name", "reason")
