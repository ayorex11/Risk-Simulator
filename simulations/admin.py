from django.contrib import admin
from .models import BusinessProcess, ScenarioTemplate, Simulation, SimulationResult

@admin.register(BusinessProcess)
class BusinessProcessAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'criticality_level', 'created_at']
    list_filter = ['criticality_level', 'organization']

@admin.register(ScenarioTemplate)
class ScenarioTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'scenario_type', 'is_active']
    list_filter = ['scenario_type', 'is_active']

@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    list_display = ['name', 'target_vendor', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'scenario_template', 'created_at']
    search_fields = ['name', 'target_vendor__name']

@admin.register(SimulationResult)
class SimulationResultAdmin(admin.ModelAdmin):
    list_display = ['simulation', 'total_financial_impact', 'downtime_hours', 'created_at']