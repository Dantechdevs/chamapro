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
]