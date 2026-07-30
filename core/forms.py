from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import BloodInventory, DonationAppointment, EmergencyRequest, HospitalProfile, User


FORM_INPUT_CLASS = "ui-input"
FORM_SELECT_CLASS = "ui-select"


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "you@example.com",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email address"


class RegistrationForm(forms.ModelForm):
    hospital_name = forms.CharField(
        label="Hospital name",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "Hospital or blood bank name",
            }
        ),
    )
    registration_number = forms.CharField(
        label="Registration number",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "Optional registration number",
            }
        ),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(
            attrs={
                "class": FORM_INPUT_CLASS,
                "placeholder": "Re-enter your password",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "role"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": FORM_INPUT_CLASS, "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": FORM_INPUT_CLASS, "placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"class": FORM_INPUT_CLASS, "placeholder": "you@example.com"}),
            "phone_number": forms.TextInput(attrs={"class": FORM_INPUT_CLASS, "placeholder": "+91..."}),
            "role": forms.Select(attrs={"class": FORM_SELECT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (User.Role.DONOR, "Donor"),
            (User.Role.HOSPITAL, "Hospital"),
        ]
        self.fields["role"].widget.attrs["class"] = FORM_SELECT_CLASS

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        hospital_name = cleaned_data.get("hospital_name")

        if role == User.Role.HOSPITAL and not hospital_name:
            self.add_error("hospital_name", "Hospital name is required for hospital accounts.")
        return cleaned_data

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        if password2:
            validate_password(password2, user=User(email=self.cleaned_data.get("email", "")))
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower().strip()
        user.set_password(self.cleaned_data["password1"])
        user.is_approved = user.role != User.Role.HOSPITAL
        if commit:
            user.save()
            if user.role == User.Role.HOSPITAL:
                from .models import HospitalProfile

                HospitalProfile.objects.create(
                    user=user,
                    hospital_name=self.cleaned_data["hospital_name"],
                    registration_number=self.cleaned_data.get("registration_number", ""),
                )
        return user


class DonationAppointmentForm(forms.ModelForm):
    hospital = forms.ModelChoiceField(
        queryset=HospitalProfile.objects.all(),
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    survey_response = forms.CharField(
        label="Minimum requirement / health response",
        required=False,
        widget=forms.Textarea(
            attrs={"class": FORM_INPUT_CLASS, "rows": 4, "placeholder": "Answer the minimum health details here"}
        ),
    )

    class Meta:
        model = DonationAppointment
        fields = ["hospital", "appointment_datetime", "survey_response", "notes"]
        widgets = {
            "appointment_datetime": forms.DateTimeInput(
                attrs={"class": FORM_INPUT_CLASS, "type": "datetime-local"}
            ),
            "notes": forms.Textarea(attrs={"class": FORM_INPUT_CLASS, "rows": 3, "placeholder": "Optional notes"}),
        }

    def clean_survey_response(self):
        response = self.cleaned_data.get("survey_response", "").strip()
        if not response:
            return {}
        return {"minimum_requirement": response}


class BloodRequestForm(forms.ModelForm):
    hospital = forms.ModelChoiceField(
        queryset=HospitalProfile.objects.all(),
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    class Meta:
        model = EmergencyRequest
        fields = ["hospital", "blood_group", "units_required", "reason"]
        widgets = {
            "blood_group": forms.Select(attrs={"class": FORM_SELECT_CLASS}),
            "units_required": forms.NumberInput(attrs={"class": FORM_INPUT_CLASS, "min": 1}),
            "reason": forms.Textarea(
                attrs={"class": FORM_INPUT_CLASS, "rows": 3, "placeholder": "State the reason for blood request"}
            ),
        }

    def clean_units_required(self):
        units = self.cleaned_data["units_required"]
        if units < 1:
            raise forms.ValidationError("At least one unit must be requested.")
        return units
