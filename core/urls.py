from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('users/me/', views.get_current_user, name='current-user'),
    path('users/me/update/', views.update_current_user, name='update-current-user'),
    path('users/', views.list_users, name='list-users'),
    path('users/<uuid:user_id>/', views.get_user_detail, name='user-detail'),
    path('users/<uuid:user_id>/update/', views.update_user, name='update-user'),
    path('users/<uuid:user_id>/profile/', views.update_user_profile, name='update-profile'),
    path('users/permissions/', views.get_user_permissions, name='user-permissions'),
    path('organization/', views.get_organization, name='organization'),
    path('organization/update/', views.update_organization, name='update-organization'),
    path('organization/create/', views.create_organization, name='create-organization'),
    path('organization/stats/', views.get_organization_stats, name='organization-stats'),
    path('organization/dashboard/', views.get_dashboard_overview, name='dashboard-overview'),
    path('organization/<uuid:organization_id>/request/', views.send_request_to_organization, name='organization-request'),
    path('organization/request_list/', views.get_request_list, name='organization-request'),
    path('organization/<uuid:request_id>/approve/', views.approve_request, name='approve-request'),
]