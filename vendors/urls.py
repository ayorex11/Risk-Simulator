from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('', views.vendor_list_create, name='vendor-list-create'),
    path('<uuid:vendor_id>/', views.vendor_detail, name='vendor-detail'),
    path('<uuid:vendor_id>/recalculate-risk/', views.recalculate_vendor_risk, name='recalculate-risk'),
    path('<uuid:vendor_id>/risk-history/', views.vendor_risk_history, name='risk-history'),
    path('<uuid:vendor_id>/dependencies/', views.vendor_dependencies, name='dependencies'),
    path('summary/', views.vendor_summary, name='vendor-summary'),
    path('compare/', views.compare_vendors, name='compare-vendors'),
    path('incidents/', views.incident_list_create, name='incident-list-create'),
    path('incidents/<uuid:incident_id>/', views.incident_detail, name='incident-detail'),
    path('incidents/trends/', views.incident_trends, name='incident-trends'),
    path('certifications/', views.certification_list_create, name='certification-list-create'),
    path('certifications/expiring/', views.certification_expiring_soon, name='certifications-expiring'),
    path('<uuid:vendor_id>/contacts/', views.vendor_contact_list_create, name='contact-list-create'),
]