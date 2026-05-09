# ChamaPro – Investments Module

A full unit-ledger investment tracking system for ChamaPro.

## Files Included

```
investments/
├── __init__.py
├── apps.py
├── models.py          ← 5 models: Investment, InvestmentUnit, InvestmentReturn,
│                          ReturnDistribution, NAVHistory
├── forms.py           ← InvestmentForm, InvestmentReturnForm, NAVUpdateForm, IssueUnitsForm
├── views.py           ← 8 views: portfolio, detail, add, edit, log_return,
│                          update_nav, issue_units, member_stakes
├── urls.py            ← URL patterns
├── services.py        ← Business logic: issue_units, process_return, update_nav,
│                          portfolio_summary, member_portfolio
├── admin.py           ← Django admin registrations
├── migrations/
│   └── 0001_initial.py
└── templates/
    └── investments/
        ├── portfolio.html   ← Overview with hero, stats, type breakdown
        ├── detail.html      ← 4-tab detail: NAV chart, unit holders, returns, distributions
        ├── add.html         ← Add / Edit investment form with visual type picker
        └── stakes.html      ← Per-member position view
```

---

## Setup

### 1. Copy the `investments/` folder into your Django project root

### 2. Add to `INSTALLED_APPS` in `settings.py`
```python
INSTALLED_APPS = [
    ...
    'investments',
]
```

### 3. Include URLs in your project's `urls.py`
```python
from django.urls import path, include

urlpatterns = [
    ...
    path('chama/', include('investments.urls')),
]
```

### 4. Update the sidebar link in `base.html`
Replace the `#` href with the real URL:
```html
<a href="{% url 'investments_portfolio' chama.id %}" class="nav-link-cp {% block nav_investments %}{% endblock %}">
  <i class="fas fa-chart-pie"></i> Investments
</a>
```
And remove the `<span class="badge-soon">SOON</span>`.

Also add `{% block nav_investments %}{% endblock %}` to the block list.

### 5. Run migrations
```bash
python manage.py migrate investments
```

### 6. Adjust the migration dependency
In `migrations/0001_initial.py`, update the `dependencies` list to match
your actual last `chama` app migration:
```python
dependencies = [
    ('chama', '0005_your_last_migration'),   # ← update this
    ('auth', '0012_alter_user_first_name_max_length'),
]
```

### 7. Wire up wallet credits (optional but recommended)
In `services.py`, find `_credit_wallet()` and connect it to your wallet system:
```python
def _credit_wallet(membership, amount, investment_return):
    from wallets.services import credit_member_wallet
    credit_member_wallet(
        membership=membership,
        amount=amount,
        description=f"Return from {investment_return.investment.name}",
        reference=f"INV-RET-{investment_return.pk}",
    )
```

---

## Key Concepts

### Units
Each investment starts with NAV = 1.0 (1 unit = KES 1).
When a member is issued units, the amount is divided by current NAV to get units issued.
As the investment grows, NAV rises and existing units become worth more.

### NAV (Net Asset Value)
`NAV = total_current_value / total_units_in_circulation`

Update NAV manually via "Update NAV" button on the detail page, or automatically
when a return is reinvested.

### Return Flows
- **Reinvest**: adds gross_amount to investment's current_value, updates NAV
- **Distribute**: splits gross_amount proportionally by units held, credits each member's wallet

---

## Pages

| URL | Name | Description |
|-----|------|-------------|
| `/chama/<id>/investments/` | `investments_portfolio` | Portfolio overview |
| `/chama/<id>/investments/add/` | `investment_add` | Add new investment |
| `/chama/<id>/investments/<pk>/` | `investment_detail` | Detail + actions |
| `/chama/<id>/investments/<pk>/edit/` | `investment_edit` | Edit investment |
| `/chama/<id>/investments/<pk>/return/` | `investment_log_return` | POST: log return |
| `/chama/<id>/investments/<pk>/nav/` | `investment_update_nav` | POST: update NAV |
| `/chama/<id>/investments/<pk>/issue-units/` | `investment_issue_units` | POST: issue units |
| `/chama/<id>/investments/stakes/` | `investment_stakes` | Member stakes view |
