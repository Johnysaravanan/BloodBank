from rest_framework import serializers

from .models import BloodInventory, DonationAppointment, EmergencyRequest, HospitalProfile, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "is_approved",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["is_approved", "is_active", "date_joined"]


class HospitalProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source="user", queryset=User.objects.all(), write_only=True)

    class Meta:
        model = HospitalProfile
        fields = [
            "id",
            "user",
            "user_id",
            "hospital_name",
            "registration_number",
            "address",
            "city",
            "state",
            "pincode",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class BloodInventorySerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source="hospital.hospital_name", read_only=True)

    class Meta:
        model = BloodInventory
        fields = ["id", "hospital", "hospital_name", "blood_group", "units_available", "updated_at"]
        read_only_fields = ["updated_at"]


class DonationAppointmentSerializer(serializers.ModelSerializer):
    donor_email = serializers.EmailField(source="donor.email", read_only=True)
    hospital_name = serializers.CharField(source="hospital.hospital_name", read_only=True)

    class Meta:
        model = DonationAppointment
        fields = [
            "id",
            "donor",
            "donor_email",
            "hospital",
            "hospital_name",
            "appointment_datetime",
            "eligibility_status",
            "survey_response",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class EmergencyRequestSerializer(serializers.ModelSerializer):
    requester_email = serializers.EmailField(source="requester.email", read_only=True)
    hospital_name = serializers.CharField(source="hospital.hospital_name", read_only=True)

    class Meta:
        model = EmergencyRequest
        fields = [
            "id",
            "requester",
            "requester_email",
            "hospital",
            "hospital_name",
            "blood_group",
            "units_required",
            "status",
            "reason",
            "fulfilled_units",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["fulfilled_units", "created_at", "updated_at"]
