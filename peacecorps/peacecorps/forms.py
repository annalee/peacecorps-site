from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from localflavor.us.us_states import STATE_CHOICES

from .models import Country


class DonationPaymentForm(forms.Form):
    """Collect contact information and dedication information about a donor"""

    PAYMENT_TYPE_CHOICES = (
        ('CreditCard', 'Credit Card'),
        ('CreditACH', 'ACH Bank Check'),
    )

    is_org = forms.BooleanField(
        label="I'm donating on behalf of my organization", required=False)
    #   Will be hidden if "Organization" is selected
    payer_name = forms.CharField(label="Name", max_length=100, required=False,
            error_messages={'required': 'Please enter your full name'})
    #   Will be hidden in "Individual is selected"
    organization_name = forms.CharField(
        label='Organization Name', max_length=40, required=False)
    organization_contact = forms.CharField(
        label='Contact Person', max_length=100, required=False)

    email = forms.EmailField(required=False)
    # Be sure that country is processed before billing_state/zip
    country = forms.ModelChoiceField(
        queryset=Country.objects, to_field_name='code', initial='USA')
    billing_address = forms.CharField(label="Street Address", max_length=80,
            error_messages={'required': 'Please enter a valid address'})
    billing_address_extra = forms.CharField(
        label="Street Address (cont)", max_length=80, required=False)
    billing_city = forms.CharField(label="City", max_length=40,
            error_messages={'required': 'Please enter a valid city'})
    billing_state = forms.ChoiceField(
        label="State", choices=((('', ''),) + STATE_CHOICES), required=False)
    billing_zip = forms.CharField(required=False)
    phone_number = forms.CharField(required=False, max_length=15)
    payment_type = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_TYPE_CHOICES,
        initial="CreditCard",
    )
    comments = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}))

    # Dedication related fields - all except the first will only be visible if
    # dedication is True
    dedication = forms.BooleanField(initial=False, required=False)
    DEDICATION_TYPE_CHOICES = (
        ('in-honor', 'in honor'),
        ('in-memory', 'in memory')
    )
    ded_yes = "I authorize the Peace Corps to make my name and contact"
    ded_yes += " information available to the honoree."
    ded_no = "I do not authorize the Peace Corps to make my name and contact"
    ded_no += " information available to the honoree."
    DEDICATION_CONSENT_CHOICES = (
        ('yes-dedication-consent', ded_yes),
        ('no-dedication-consent', ded_no),
    )
    dedication_name = forms.CharField(
        label="Name", max_length=40, required=False)
    dedication_type = forms.ChoiceField(
        widget=forms.RadioSelect, choices=DEDICATION_TYPE_CHOICES,
        initial='in-honor', required=False)
    dedication_contact = forms.CharField(
        label="Family Contact", max_length=40, required=False)
    dedication_email = forms.EmailField(label="Email", required=False)
    dedication_address = forms.CharField(
        label="Mailing Address", max_length=255, required=False)
    card_dedication = forms.CharField(max_length=150, required=False,
                                widget=forms.Textarea(attrs={'rows': 2}))
    dedication_consent = forms.ChoiceField(
        widget=forms.RadioSelect, initial='yes-dedication-consent',
        choices=DEDICATION_CONSENT_CHOICES, required=False)

    # User consents to stay informed about the Peace Corps.
    email_consent = forms.BooleanField(initial=True, required=False)

    # True if there might be a possible conflict of interest.
    interest_conflict = forms.BooleanField(initial=False, required=False)

    information_consent = forms.BooleanField(
        label='Make my contact info available to the volunteer',
        required=False, initial=True)

    payment_amount = forms.IntegerField(widget=forms.HiddenInput())
    project_code = forms.CharField(max_length=40, widget=forms.HiddenInput())

    def required_when(self, guard_field, guard_value, check_field, field_name):
        """Raises a validation error when both the field with name guard_field
        is equal to guard_value and the field with name check_field is
        empty"""
        if (self.cleaned_data.get(guard_field) == guard_value
                and not self.cleaned_data.get(check_field)):
            raise ValidationError('Please enter ' +
                    field_name)
        return self.cleaned_data.get(check_field)

    def clean_payer_name(self):
        return self.required_when('is_org', False, 'payer_name',
                'your full name')

    def clean_organization_name(self):
        return self.required_when('is_org', True, 'organization_name',
                'your organization\'s name')

    def clean_organization_contact(self):
        return self.required_when('is_org', True, 'organization_contact',
                'your organization\'s contact')

    def clean_billing_state(self):
        """Can't use required_when because the country field returns a model"""
        country = self.cleaned_data.get('country')
        state = self.cleaned_data.get('billing_state')
        if country and country.code == 'USA' and not state:
            raise ValidationError('Please select a valid state')
        return state

    def clean_billing_zip(self):
        country = self.cleaned_data.get('country')
        zip = self.cleaned_data.get('billing_zip')
        if country and country.code == 'USA' and not zip:
            raise ValidationError('Please enter a valid zip code')
        return zip

    def clean(self):
        """Only one of the organization/individual set of fields should be
        present. Blank out the other"""
        if self.cleaned_data.get('is_org'):
            del self.cleaned_data['payer_name']
        else:
            del self.cleaned_data['organization_name']
            del self.cleaned_data['organization_contact']
        return self.cleaned_data


class DonationAmountForm(forms.Form):
    """Validation of donation amounts."""
    presets = forms.ChoiceField(
        widget=forms.RadioSelect, initial='preset-50',
        choices=(('preset-50', '50'),
                 ('preset-100', '100'),
                 ('custom', 'Custom')))
    # required if "custom" is selected above. Min value of $1, as anything
    # lower than that will cost too much money to process. Max value of
    # $9,999.99, as anything above that can't be processed by pay.gov
    payment_amount = forms.DecimalField(max_value=9999.99, min_value=1,
                                        decimal_places=2, required=False)

    def clean_payment_amount(self):
        """Selecting a preset is identical to typing the exact amount"""
        for amt in (50, 100):
            if self.cleaned_data.get('presets') == 'preset-' + str(amt):
                return Decimal(amt)
        if self.cleaned_data.get('payment_amount'):
            return self.cleaned_data.get('payment_amount')
        raise ValidationError('This field is required.')
