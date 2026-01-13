from rest_framework import serializers
from .models import (
    BusinessProcess, ScenarioTemplate, Simulation,
    SimulationResult, SimulationScenario, SimulationComparison
)
from vendors.serializers import VendorListSerializer


class BusinessProcessSerializer(serializers.ModelSerializer):
    """Serializer for BusinessProcess"""
    dependent_vendor_names = serializers.SerializerMethodField()
    criticality_display = serializers.CharField(
        source='get_criticality_level_display',
        read_only=True
    )
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessProcess
        fields = [
            'id', 'organization', 'name', 'description',
            'criticality_level', 'criticality_display',
            'hourly_operating_cost', 'annual_revenue_contribution',
            'dependent_vendors', 'dependent_vendor_names',
            'owner', 'owner_name', 'department',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_dependent_vendor_names(self, obj):
        return [vendor.name for vendor in obj.dependent_vendors.all()]
    
    def get_owner_name(self, obj):
        if obj.owner:
            return f"{obj.owner.first_name} {obj.owner.last_name}".strip()
        return None
    
    def create(self, validated_data):
        """Set organization from request context"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['organization'] = request.user.profile.organization
        return super().create(validated_data)


class BusinessProcessListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for process lists"""
    criticality_display = serializers.CharField(
        source='get_criticality_level_display',
        read_only=True
    )
    
    class Meta:
        model = BusinessProcess
        fields = [
            'id', 'name', 'criticality_level', 'criticality_display',
            'hourly_operating_cost'
        ]
        read_only_fields = fields


class ScenarioTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ScenarioTemplate"""
    scenario_type_display = serializers.CharField(
        source='get_scenario_type_display',
        read_only=True
    )
    
    class Meta:
        model = ScenarioTemplate
        fields = [
            'id', 'scenario_type', 'scenario_type_display', 'name',
            'description', 'default_parameters', 'calculation_config',
            'is_active', 'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SimulationScenarioSerializer(serializers.ModelSerializer):
    """Serializer for custom simulation scenarios"""
    base_template_name = serializers.CharField(
        source='base_template.name',
        read_only=True
    )
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SimulationScenario
        fields = [
            'id', 'organization', 'name', 'description',
            'base_template', 'base_template_name', 'custom_parameters',
            'is_default', 'is_shared', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None


class SimulationResultSerializer(serializers.ModelSerializer):
    """Serializer for SimulationResult"""
    affected_process_names = serializers.SerializerMethodField()
    recovery_complexity_display = serializers.CharField(
        source='get_recovery_complexity_display',
        read_only=True
    )
    
    class Meta:
        model = SimulationResult
        fields = [
            'id', 'simulation', 'direct_costs', 'operational_costs',
            'regulatory_costs', 'reputational_costs', 'total_financial_impact',
            'affected_processes', 'affected_process_names', 'downtime_hours',
            'productivity_loss_percentage', 'customers_affected',
            'estimated_recovery_time_hours', 'recovery_complexity',
            'recovery_complexity_display', 'cascading_vendor_impacts',
            'total_cascading_impact', 'monte_carlo_results',
            'impact_breakdown', 'risk_score', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_affected_process_names(self, obj):
        return [process.name for process in obj.affected_processes.all()]


class SimulationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for simulation lists"""
    scenario_name = serializers.CharField(
        source='scenario_template.name',
        read_only=True
    )
    vendor_name = serializers.CharField(
        source='target_vendor.name',
        read_only=True
    )
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    has_results = serializers.SerializerMethodField()
    
    class Meta:
        model = Simulation
        fields = [
            'id', 'name', 'scenario_name', 'vendor_name',
            'status', 'status_display', 'created_by', 'created_by_name',
            'created_at', 'completed_at', 'execution_time', 'has_results'
        ]
        read_only_fields = fields
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None
    
    def get_has_results(self, obj):
        return hasattr(obj, 'result')


class SimulationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for simulation with all data"""
    scenario_template_data = ScenarioTemplateSerializer(
        source='scenario_template',
        read_only=True
    )
    vendor_data = VendorListSerializer(
        source='target_vendor',
        read_only=True
    )
    result = SimulationResultSerializer(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = Simulation
        fields = '__all__'
        read_only_fields = [
            'id', 'status', 'started_at', 'completed_at',
            'execution_time', 'created_at', 'updated_at'
        ]
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None


class SimulationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating simulations"""
    
    class Meta:
        model = Simulation
        fields = [
            'name', 'description', 'scenario_template', 'target_vendor',
            'parameters', 'use_monte_carlo', 'monte_carlo_iterations', 'tags'
        ]
    
    def validate_monte_carlo_iterations(self, value):
        """Validate Monte Carlo iterations"""
        from django.conf import settings
        max_iterations = settings.SIMULATION_CONFIG.get('MAX_MONTE_CARLO_ITERATIONS', 10000)
        if value > max_iterations:
            raise serializers.ValidationError(
                f"Maximum iterations is {max_iterations}"
            )
        return value
    
    def validate(self, data):
        """Validate simulation data"""
        # If use_monte_carlo is True, ensure iterations is set
        if data.get('use_monte_carlo') and not data.get('monte_carlo_iterations'):
            data['monte_carlo_iterations'] = 1000  # Default
        
        return data
    
    def create(self, validated_data):
        """Create simulation with organization context"""
        request = self.context.get('request')
        if request:
            if hasattr(request.user, 'profile'):
                validated_data['organization'] = request.user.profile.organization
            validated_data['created_by'] = request.user
        
        return Simulation.objects.create(**validated_data)


class SimulationExecutionSerializer(serializers.Serializer):
    """Serializer for simulation execution request"""
    simulation_id = serializers.UUIDField()
    force_rerun = serializers.BooleanField(default=False)


class WhatIfAnalysisSerializer(serializers.Serializer):
    """Serializer for what-if analysis requests"""
    base_simulation_id = serializers.UUIDField()
    parameter_changes = serializers.JSONField()
    scenario_name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)


class SimulationComparisonRequestSerializer(serializers.Serializer):
    """Serializer for comparing multiple simulations"""
    simulation_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=2,
        max_length=10
    )
    comparison_metrics = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class SimulationComparisonSerializer(serializers.ModelSerializer):
    """Serializer for saved simulation comparisons"""
    simulation_names = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SimulationComparison
        fields = [
            'id', 'organization', 'name', 'description',
            'simulations', 'simulation_names', 'comparison_data',
            'notes', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_simulation_names(self, obj):
        return [sim.name for sim in obj.simulations.all()]
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None


class SimulationComparisonResultSerializer(serializers.Serializer):
    """Serializer for comparison analysis results"""
    simulations = SimulationListSerializer(many=True)
    
    comparison_metrics = serializers.DictField(
        child=serializers.ListField()
    )
    
    summary_statistics = serializers.DictField()
    
    visualizations = serializers.DictField(
        child=serializers.ListField()
    )
    
    recommendations = serializers.ListField(
        child=serializers.CharField()
    )


class SimulationSummarySerializer(serializers.Serializer):
    """Serializer for simulation portfolio summary"""
    total_simulations = serializers.IntegerField()
    completed_simulations = serializers.IntegerField()
    pending_simulations = serializers.IntegerField()
    failed_simulations = serializers.IntegerField()
    
    total_estimated_impact = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_recovery_time = serializers.FloatField()
    
    by_scenario_type = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    by_vendor = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    recent_simulations = SimulationListSerializer(many=True)
    highest_impact_scenarios = SimulationListSerializer(many=True)


class MonteCarloResultSerializer(serializers.Serializer):
    """Serializer for Monte Carlo simulation results"""
    iterations = serializers.IntegerField()
    
    statistics = serializers.DictField(
        child=serializers.FloatField()
    )
    
    percentiles = serializers.DictField(
        child=serializers.FloatField()
    )
    
    confidence_intervals = serializers.DictField()
    
    distribution_data = serializers.ListField(
        child=serializers.FloatField()
    )


class ImpactBreakdownSerializer(serializers.Serializer):
    """Serializer for detailed impact breakdown"""
    financial_impact = serializers.DictField(
        child=serializers.DecimalField(max_digits=15, decimal_places=2)
    )
    
    operational_impact = serializers.DictField()
    
    affected_resources = serializers.DictField()
    
    timeline = serializers.ListField(
        child=serializers.DictField()
    )
    
    mitigation_options = serializers.ListField(
        child=serializers.DictField()
    )


class BatchSimulationSerializer(serializers.Serializer):
    """Serializer for running multiple simulations at once"""
    vendor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    scenario_template_id = serializers.UUIDField()
    base_parameters = serializers.JSONField()
    use_monte_carlo = serializers.BooleanField(default=False)
    monte_carlo_iterations = serializers.IntegerField(default=1000)