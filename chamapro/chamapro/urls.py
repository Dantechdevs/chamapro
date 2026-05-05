from django.contrib import admin
from django.urls import include, path
from chamapro import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public
    path('', views.home, name='home'),
    path('features/', views.features, name='features'),
    path('pricing/', views.pricing, name='pricing'),
    path('customers/', views.customers, name='customers'),

    # Auth
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/switch/<int:chama_id>/', views.switch_chama, name='switch_chama'),

    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/kyc/', views.profile_kyc, name='profile_kyc'),

    # Chama management
    path('chama/create/', views.chama_create, name='chama_create'),
    path('chama/<int:chama_id>/members/', views.chama_members, name='chama_members'),
    path('chama/<int:chama_id>/invite/', views.member_invite, name='member_invite'),
    path('chama/<int:chama_id>/members/<int:membership_id>/role/', views.member_role_update, name='member_role_update'),
    path('chama/<int:chama_id>/members/<int:membership_id>/remove/', views.member_remove, name='member_remove'),

    # Contributions
    path('chama/<int:chama_id>/contributions/', views.contributions, name='contributions'),
    path('chama/<int:chama_id>/contributions/add/', views.contribution_add, name='contribution_add'),
    path('chama/<int:chama_id>/contributions/<int:contribution_id>/delete/', views.contribution_delete, name='contribution_delete'),
    path('chama/<int:chama_id>/contributions/<int:contribution_id>/status/', views.contribution_status_update, name='contribution_status_update'),

    # Penalties
    path('chama/<int:chama_id>/penalties/add/', views.penalty_add, name='penalty_add'),

    # Loans
    path('chama/<int:chama_id>/loans/', views.loans, name='loans'),
    path('chama/<int:chama_id>/loans/apply/', views.loan_apply, name='loan_apply'),
    path('chama/<int:chama_id>/loans/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    path('chama/<int:chama_id>/loans/<int:loan_id>/approve/', views.loan_approve, name='loan_approve'),
    path('chama/<int:chama_id>/loans/<int:loan_id>/repay/', views.loan_repayment_add, name='loan_repayment_add'),

    # Reports & Exports
    path('chama/<int:chama_id>/reports/', views.reports, name='reports'),
    path('chama/<int:chama_id>/export/contributions/csv/', views.export_contributions_csv, name='export_contributions_csv'),
    path('chama/<int:chama_id>/export/loans/csv/', views.export_loans_csv, name='export_loans_csv'),
    path('chama/<int:chama_id>/export/members/csv/', views.export_members_csv, name='export_members_csv'),
    path('chama/<int:chama_id>/export/pdf/', views.export_report_pdf, name='export_report_pdf'),
    path('chama/<int:chama_id>/export/excel/', views.export_report_excel, name='export_report_excel'),

    # M-Pesa
    path('chama/<int:chama_id>/mpesa/push/', views.mpesa_stk_push, name='mpesa_stk_push'),
    path('chama/<int:chama_id>/mpesa/query/', views.mpesa_stk_query, name='mpesa_stk_query'),
    path('chama/<int:chama_id>/mpesa/transactions/', views.mpesa_transactions, name='mpesa_transactions'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),

    # Wallets app
    path('wallets/', include('wallets.urls')),
]