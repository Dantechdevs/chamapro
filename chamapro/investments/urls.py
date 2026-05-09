from django.urls import path
from . import views

app_name = 'investments'

urlpatterns = [
    # Portfolio overview
    path('<int:chama_id>/investments/',               views.portfolio,         name='portfolio'),  # ← fixed

    # Individual investment CRUD
    path('<int:chama_id>/investments/add/',           views.investment_add,    name='investment_add'),
    path('<int:chama_id>/investments/<int:pk>/',      views.investment_detail, name='investment_detail'),
    path('<int:chama_id>/investments/<int:pk>/edit/', views.investment_edit,   name='investment_edit'),

    # Actions on an investment
    path('<int:chama_id>/investments/<int:pk>/return/',      views.log_return,       name='investment_log_return'),
    path('<int:chama_id>/investments/<int:pk>/nav/',         views.update_nav_view,  name='investment_update_nav'),
    path('<int:chama_id>/investments/<int:pk>/issue-units/', views.issue_units_view, name='investment_issue_units'),

    # Cross-investment member view
    path('<int:chama_id>/investments/stakes/',        views.member_stakes,     name='investment_stakes'),
]