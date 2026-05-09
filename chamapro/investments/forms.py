from django import forms
from .models import Investment, InvestmentReturn, NAVHistory


class InvestmentForm(forms.ModelForm):
    class Meta:
        model = Investment
        fields = [
            'name', 'investment_type', 'institution',
            'capital_invested', 'date_invested', 'maturity_date',
            'current_value', 'status', 'notes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CIC Money Market Fund'}),
            'investment_type': forms.Select(attrs={'class': 'form-select'}),
            'institution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CIC Asset Managers'}),
            'capital_invested': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'date_invested': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'maturity_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'current_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes…'}),
        }

    def clean(self):
        cleaned = super().clean()
        capital = cleaned.get('capital_invested')
        current = cleaned.get('current_value')
        if current is None and capital:
            cleaned['current_value'] = capital
        return cleaned


class InvestmentReturnForm(forms.ModelForm):
    class Meta:
        model = InvestmentReturn
        fields = ['return_type', 'gross_amount', 'date_received', 'flow', 'notes']
        widgets = {
            'return_type': forms.Select(attrs={'class': 'form-select'}),
            'gross_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'date_received': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'flow': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class NAVUpdateForm(forms.ModelForm):
    class Meta:
        model = NAVHistory
        fields = ['date', 'total_value', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_value': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Current total value'}),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Q2 valuation update'}),
        }


class IssueUnitsForm(forms.Form):
    member_id      = forms.IntegerField(widget=forms.HiddenInput())
    amount         = forms.DecimalField(
        max_digits=14, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Amount (KES)'})
    )
