from django.contrib import admin
from .models import Vendor, IncidentHistory, ComplianceCertification, VendorContact

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'risk_level', 'overall_risk_score', 'created_at']
    list_filter = ['risk_level', 'industry', 'is_active']
    search_fields = ['name', 'services_provided']

@admin.register(IncidentHistory)
class IncidentHistoryAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'incident_date', 'incident_type', 'severity']
    list_filter = ['incident_type', 'severity', 'incident_date']

@admin.register(ComplianceCertification)
class ComplianceCertificationAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'certification_type', 'expiry_date', 'is_active']
    list_filter = ['certification_type', 'is_active']

@admin.register(VendorContact)
class VendorContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'vendor', 'contact_type', 'email']
    list_filter = ['contact_type']