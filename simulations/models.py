
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import Organization
from vendors.models import Vendor
import uuid

class BusinessProcess(models.Model):
    """Critical business processes"""
    CRITICALITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
        (5, 'Mission Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='business_processes'
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    criticality_level = models.IntegerField(
        choices=CRITICALITY_CHOICES,
        default=3,
        help_text="Business criticality (1-5, 5 being most critical)"
    )
    
    # Financial metrics
    hourly_operating_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Estimated cost per hour when process is down"
    )
    annual_revenue_contribution = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Annual revenue contribution of this process"
    )
    
    # Vendor dependencies
    dependent_vendors = models.ManyToManyField(
        Vendor,
        related_name='supports_processes',
        blank=True
    )
    
    # Additional details
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_processes'
    )
    department = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'business_processes'
        ordering = ['-criticality_level', 'name']
        verbose_name = 'Business Process'
        verbose_name_plural = 'Business Processes'
        unique_together = ['organization', 'name']
    
    def __str__(self):
        return f"{self.name} (Criticality: {self.criticality_level})"


class ScenarioTemplate(models.Model):
    """Predefined incident scenario types"""
    SCENARIO_TYPES = [
        ('data_breach', 'Data Breach'),
        ('ransomware', 'Ransomware Attack'),
        ('service_disruption', 'Service Disruption'),
        ('supply_chain', 'Supply Chain Compromise'),
        ('multi_vendor', 'Multi-Vendor Failure'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    scenario_type = models.CharField(max_length=50, choices=SCENARIO_TYPES, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Default parameters (JSON structure)
    default_parameters = models.JSONField(
        default=dict,
        help_text="Default parameters for this scenario type"
    )
    
    # Impact calculation methods
    calculation_config = models.JSONField(
        default=dict,
        help_text="Configuration for impact calculations"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    version = models.CharField(max_length=20, default='1.0')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scenario_templates'
        ordering = ['name']
        verbose_name = 'Scenario Template'
        verbose_name_plural = 'Scenario Templates'
    
    def __str__(self):
        return self.name


class Simulation(models.Model):
    """Simulation execution records"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='simulations'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_simulations'
    )
    
    # Simulation configuration
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scenario_template = models.ForeignKey(
        ScenarioTemplate,
        on_delete=models.CASCADE,
        related_name='simulations'
    )
    target_vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='simulations'
    )
    
    # Simulation parameters (JSON)
    parameters = models.JSONField(
        default=dict,
        help_text="Specific parameters for this simulation run"
    )
    
    # Monte Carlo settings
    use_monte_carlo = models.BooleanField(
        default=False,
        help_text="Use Monte Carlo simulation for probabilistic analysis"
    )
    monte_carlo_iterations = models.IntegerField(
        default=1000,
        validators=[MinValueValidator(100), MaxValueValidator(10000)],
        help_text="Number of Monte Carlo iterations (100-10000)"
    )
    
    # Execution details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    execution_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Execution time in seconds"
    )
    
    # Error handling
    error_message = models.TextField(blank=True)
    
    # Tags for organization
    tags = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'simulations'
        ordering = ['-created_at']
        verbose_name = 'Simulation'
        verbose_name_plural = 'Simulations'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['target_vendor', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.scenario_template.name}"


class SimulationResult(models.Model):
    """Detailed impact predictions from simulations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    simulation = models.OneToOneField(
        Simulation,
        on_delete=models.CASCADE,
        related_name='result'
    )
    
    # Financial impacts (in USD)
    direct_costs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Direct incident response and remediation costs"
    )
    operational_costs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Business disruption and productivity loss costs"
    )
    regulatory_costs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Fines, penalties, and legal costs"
    )
    reputational_costs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Customer churn and brand damage costs"
    )
    total_financial_impact = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total financial impact"
    )
    
    # Operational impacts
    affected_processes = models.ManyToManyField(
        BusinessProcess,
        related_name='impacted_by_simulations',
        blank=True
    )
    downtime_hours = models.FloatField(
        default=0,
        help_text="Estimated hours of downtime"
    )
    productivity_loss_percentage = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of productivity loss"
    )
    customers_affected = models.IntegerField(
        default=0,
        help_text="Number of customers potentially affected"
    )
    
    # Recovery estimates
    estimated_recovery_time_hours = models.FloatField(
        default=0,
        help_text="Estimated time to full recovery (hours)"
    )
    recovery_complexity = models.CharField(
        max_length=50,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('very_high', 'Very High'),
        ],
        default='medium'
    )
    
    # Cascading effects
    cascading_vendor_impacts = models.JSONField(
        default=list,
        help_text="List of affected vendors and their impacts"
    )
    total_cascading_impact = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total financial impact from cascading failures"
    )
    
    # Monte Carlo results (if applicable)
    monte_carlo_results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Statistical results from Monte Carlo simulation"
    )
    # Structure: {
    #   'mean': float,
    #   'median': float,
    #   'std_dev': float,
    #   'percentile_50': float,
    #   'percentile_90': float,
    #   'percentile_95': float,
    #   'percentile_99': float,
    #   'min': float,
    #   'max': float,
    #   'confidence_intervals': {...}
    # }
    
    # Detailed breakdown (JSON)
    impact_breakdown = models.JSONField(
        default=dict,
        help_text="Detailed breakdown of all impact calculations"
    )
    
    # Risk score based on simulation
    risk_score = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Overall risk score from simulation (0-100)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'simulation_results'
        verbose_name = 'Simulation Result'
        verbose_name_plural = 'Simulation Results'
    
    def __str__(self):
        return f"Results for {self.simulation.name}"
    
    def calculate_totals(self):
        """Calculate total financial impact"""
        self.total_financial_impact = (
            self.direct_costs +
            self.operational_costs +
            self.regulatory_costs +
            self.reputational_costs +
            self.total_cascading_impact
        )
        self.save(update_fields=['total_financial_impact'])


class SimulationScenario(models.Model):
    """
    Saved simulation scenarios for reuse
    Templates created by users based on common patterns
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='custom_scenarios'
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Base scenario
    base_template = models.ForeignKey(
        ScenarioTemplate,
        on_delete=models.CASCADE,
        related_name='custom_scenarios'
    )
    
    # Customized parameters
    custom_parameters = models.JSONField(
        default=dict,
        help_text="Organization-specific parameter overrides"
    )
    
    # Metadata
    is_default = models.BooleanField(default=False)
    is_shared = models.BooleanField(
        default=False,
        help_text="Share with other users in organization"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_scenarios'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'simulation_scenarios'
        ordering = ['name']
        verbose_name = 'Custom Simulation Scenario'
        verbose_name_plural = 'Custom Simulation Scenarios'
    
    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class SimulationComparison(models.Model):
    """
    Save simulation comparisons for analysis
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='simulation_comparisons'
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Simulations being compared
    simulations = models.ManyToManyField(
        Simulation,
        related_name='comparisons'
    )
    
    # Comparison analysis
    comparison_data = models.JSONField(
        default=dict,
        help_text="Detailed comparison analysis results"
    )
    
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_comparisons'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'simulation_comparisons'
        ordering = ['-created_at']
        verbose_name = 'Simulation Comparison'
        verbose_name_plural = 'Simulation Comparisons'
    
    def __str__(self):
        return self.name