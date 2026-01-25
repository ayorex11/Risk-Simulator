from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import Organization
import uuid

class Vendor(models.Model):
    RISK_LEVEL_CHOICES = [
        ('low', 'Low (0-25)'),
        ('medium', 'Medium (26-50)'),
        ('high', 'High (51-75)'),
        ('critical', 'Critical (76-100)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='vendors'
    )
    
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    website = models.URLField(blank=True, null=True)
    
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    
    services_provided = models.TextField()
    contract_start_date = models.DateField()
    contract_end_date = models.DateField()
    contract_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    security_posture_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    data_sensitivity_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    service_criticality_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    incident_history_score = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    compliance_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    third_party_dependencies_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    overall_risk_score = models.FloatField(default=0.0, editable=False)
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='medium',
        editable=False
    )
    
    dependent_vendors = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='dependency_of',
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_vendors'
    )
    
    class Meta:
        db_table = 'vendors'
        ordering = ['-overall_risk_score', 'name']
        unique_together = ['organization', 'name']
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        indexes = [
            models.Index(fields=['organization', 'risk_level']),
            models.Index(fields=['organization', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.risk_level})"
    
    def calculate_risk_score(self):
        # Normalize variables that are not on a 0-100 scale
        ds_normalized = (self.data_sensitivity_level / 5) * 100
        sc_normalized = (self.service_criticality_level / 5) * 100
        
        # Weighted Base Score Calculation
        # IH is inverted: lower score = more incidents = higher risk
        base_score = (
            (self.security_posture_score * 0.30) +
            (ds_normalized * 0.20) +
            (sc_normalized * 0.20) +
            ((100 - self.incident_history_score) * 0.15) +
            (self.third_party_dependencies_score * 0.15)
        )
        
        # Apply Compliance Factor Mitigation [1 - (CS/100)]
        compliance_reduction = 1 - (self.compliance_score / 100)
        
        # Round final score to 3 decimal places for consistency
        self.overall_risk_score = round(base_score * compliance_reduction, 3)
        
        # Categorization based on rounded score
        if self.overall_risk_score <= 25:
            self.risk_level = 'low'
        elif self.overall_risk_score <= 50:
            self.risk_level = 'medium'
        elif self.overall_risk_score <= 75:
            self.risk_level = 'high'
        else:
            self.risk_level = 'critical'
            
        return self.overall_risk_score

    def save(self, *args, **kwargs):
        self.calculate_risk_score()
        super().save(*args, **kwargs)

    def get_dependency_chain(self, depth=0, max_depth=5, visited=None):
        if visited is None:
            visited = set()
        
        if depth >= max_depth or self.id in visited:
            return []
        
        visited.add(self.id)
        chain = [(self, depth)]
        
        for dep in self.dependent_vendors.all():
            chain.extend(dep.get_dependency_chain(depth + 1, max_depth, visited))
        
        return chain


class IncidentHistory(models.Model):
    INCIDENT_TYPES = [
        ('data_breach', 'Data Breach'),
        ('ransomware', 'Ransomware'),
        ('ddos', 'DDoS Attack'),
        ('outage', 'Service Outage'),
        ('supply_chain', 'Supply Chain Attack'),
        ('insider_threat', 'Insider Threat'),
        ('malware', 'Malware Infection'),
        ('phishing', 'Phishing Attack'),
        ('other', 'Other'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='incident_history'
    )
    
    incident_date = models.DateField()
    incident_type = models.CharField(max_length=50, choices=INCIDENT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    records_affected = models.IntegerField(default=0)
    downtime_hours = models.FloatField(default=0)
    financial_impact = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    
    time_to_detect_hours = models.FloatField(default=0)
    time_to_contain_hours = models.FloatField(default=0)
    time_to_recover_hours = models.FloatField(default=0)
    
    root_cause = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    remediation_actions = models.TextField(blank=True)
    remediation_completed = models.BooleanField(default=False)
    
    publicly_disclosed = models.BooleanField(default=False)
    disclosure_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reported_incidents'
    )
    
    class Meta:
        db_table = 'incident_history'
        ordering = ['-incident_date']
        verbose_name = 'Incident'
        verbose_name_plural = 'Incident History'
        indexes = [
            models.Index(fields=['vendor', 'incident_date']),
            models.Index(fields=['severity', 'incident_date']),
        ]
    
    def __str__(self):
        return f"{self.vendor.name} - {self.incident_type} on {self.incident_date}"
    
    @property
    def total_response_time(self):
        return self.time_to_detect_hours + self.time_to_contain_hours + self.time_to_recover_hours


class ComplianceCertification(models.Model):
    CERTIFICATION_TYPES = [
        ('iso27001', 'ISO 27001'),
        ('iso27017', 'ISO 27017 (Cloud)'),
        ('iso27018', 'ISO 27018 (Privacy)'),
        ('soc2_type1', 'SOC 2 Type I'),
        ('soc2_type2', 'SOC 2 Type II'),
        ('pci_dss', 'PCI DSS'),
        ('hipaa', 'HIPAA Compliant'),
        ('gdpr', 'GDPR Compliant'),
        ('fedramp_low', 'FedRAMP Low'),
        ('fedramp_moderate', 'FedRAMP Moderate'),
        ('fedramp_high', 'FedRAMP High'),
        ('nist_csf', 'NIST Cybersecurity Framework'),
        ('cyber_essentials', 'Cyber Essentials'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='certifications'
    )
    
    certification_type = models.CharField(max_length=50, choices=CERTIFICATION_TYPES)
    certification_body = models.CharField(max_length=255)
    
    issue_date = models.DateField()
    expiry_date = models.DateField()
    
    is_active = models.BooleanField(default=True)
    certificate_number = models.CharField(max_length=100, blank=True)
    
    certificate_file = models.FileField(
        upload_to='certifications/',
        blank=True,
        null=True
    )
    verification_url = models.URLField(blank=True, null=True)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='verified_certifications'
    )
    
    class Meta:
        db_table = 'compliance_certifications'
        ordering = ['-expiry_date']
        verbose_name = 'Certification'
        verbose_name_plural = 'Compliance Certifications'
        indexes = [
            models.Index(fields=['vendor', 'is_active']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.vendor.name} - {self.get_certification_type_display()}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now().date() > self.expiry_date
    
    def days_until_expiry(self):
        from django.utils import timezone
        delta = self.expiry_date - timezone.now().date()
        return delta.days
    
    def save(self, *args, **kwargs):
        from django.utils import timezone
        if timezone.now().date() > self.expiry_date:
            self.is_active = False
        super().save(*args, **kwargs)


class VendorContact(models.Model):
    CONTACT_TYPES = [
        ('primary', 'Primary Contact'),
        ('technical', 'Technical Contact'),
        ('security', 'Security Contact'),
        ('billing', 'Billing Contact'),
        ('legal', 'Legal Contact'),
        ('executive', 'Executive Contact'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    
    contact_type = models.CharField(max_length=20, choices=CONTACT_TYPES)
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    is_primary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vendor_contacts'
        ordering = ['-is_primary', 'name']
        verbose_name = 'Vendor Contact'
        verbose_name_plural = 'Vendor Contacts'
    
    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()}) - {self.vendor.name}"