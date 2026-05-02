from django.contrib import admin
from django.urls import path
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
]