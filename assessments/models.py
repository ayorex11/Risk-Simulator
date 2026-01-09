from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from vendors.models import Vendor
import uuid

class VendorAssessment(models.Model):
    """Security assessment questionnaire responses"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='assessments'
    )
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conducted_assessments'
    )
    
    # Assessment metadata
    assessment_date = models.DateField(auto_now_add=True)
    assessment_type = models.CharField(
        max_length=50,
        choices=[
            ('initial', 'Initial Assessment'),
            ('annual', 'Annual Review'),
            ('triggered', 'Triggered Assessment'),
            ('incident_followup', 'Incident Follow-up'),
        ],
        default='initial'
    )
    
    # Questionnaire responses (flexible JSON structure)
    responses = models.JSONField(
        default=dict,
        help_text="Detailed questionnaire responses"
    )
    
    # Assessment scores by category (0-100)
    access_control_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Access control and authentication score"
    )
    data_protection_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Data protection and encryption score"
    )
    network_security_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Network security and segmentation score"
    )
    incident_response_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Incident response capabilities score"
    )
    vulnerability_management_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Vulnerability and patch management score"
    )
    
    # Additional category scores
    business_continuity_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Business continuity and disaster recovery score"
    )
    security_governance_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Security governance and policies score"
    )
    
    # Overall assessment score (calculated)
    overall_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        editable=False
    )
    
    # Assessment status
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('approved', 'Approved'),
        ],
        default='draft'
    )
    
    # Notes and recommendations
    notes = models.TextField(blank=True, help_text="General notes about the assessment")
    findings = models.TextField(blank=True, help_text="Key findings and concerns")
    recommendations = models.TextField(blank=True, help_text="Recommendations for improvement")
    
    # Follow-up
    requires_followup = models.BooleanField(default=False)
    followup_date = models.DateField(null=True, blank=True)
    followup_completed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_assessments'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'vendor_assessments'
        ordering = ['-assessment_date']
        verbose_name = 'Vendor Assessment'
        verbose_name_plural = 'Vendor Assessments'
        indexes = [
            models.Index(fields=['vendor', 'assessment_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Assessment for {self.vendor.name} on {self.assessment_date}"
    
    def calculate_overall_score(self):
        """
        Calculate overall assessment score from category scores
        Weights based on typical security assessment priorities
        """
        self.overall_score = int(
            self.access_control_score * 0.20 +
            self.data_protection_score * 0.20 +
            self.network_security_score * 0.15 +
            self.incident_response_score * 0.15 +
            self.vulnerability_management_score * 0.15 +
            self.business_continuity_score * 0.10 +
            self.security_governance_score * 0.05
        )
        self.save(update_fields=['overall_score'])
        
        # Update vendor's security posture score
        self.vendor.security_posture_score = self.overall_score
        self.vendor.calculate_risk_score()
        
        return self.overall_score
    
    def get_score_breakdown(self):
        """Return dictionary of all category scores"""
        return {
            'access_control': self.access_control_score,
            'data_protection': self.data_protection_score,
            'network_security': self.network_security_score,
            'incident_response': self.incident_response_score,
            'vulnerability_management': self.vulnerability_management_score,
            'business_continuity': self.business_continuity_score,
            'security_governance': self.security_governance_score,
            'overall': self.overall_score,
        }


class AssessmentQuestion(models.Model):
    """
    Master list of assessment questions
    Organized by category and framework
    """
    CATEGORY_CHOICES = [
        ('access_control', 'Access Control'),
        ('data_protection', 'Data Protection'),
        ('network_security', 'Network Security'),
        ('incident_response', 'Incident Response'),
        ('vulnerability_management', 'Vulnerability Management'),
        ('business_continuity', 'Business Continuity'),
        ('security_governance', 'Security Governance'),
    ]
    
    FRAMEWORK_CHOICES = [
        ('nist', 'NIST CSF'),
        ('iso27001', 'ISO 27001'),
        ('soc2', 'SOC 2'),
        ('custom', 'Custom'),
    ]
    
    RESPONSE_TYPE_CHOICES = [
        ('yes_no', 'Yes/No'),
        ('multiple_choice', 'Multiple Choice'),
        ('rating', 'Rating (1-5)'),
        ('text', 'Free Text'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Question details
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    framework = models.CharField(max_length=20, choices=FRAMEWORK_CHOICES, default='custom')
    
    question_text = models.TextField()
    guidance = models.TextField(
        blank=True,
        help_text="Additional guidance or clarification for the question"
    )
    
    # Response configuration
    response_type = models.CharField(max_length=20, choices=RESPONSE_TYPE_CHOICES, default='yes_no')
    response_options = models.JSONField(
        default=list,
        blank=True,
        help_text="Available options for multiple choice questions"
    )
    
    # Scoring
    weight = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Question weight for scoring (1.0 = normal, higher = more important)"
    )
    max_score = models.IntegerField(
        default=100,
        help_text="Maximum score for this question"
    )
    
    # Metadata
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order within category")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_questions'
    )
    
    class Meta:
        db_table = 'assessment_questions'
        ordering = ['category', 'order', 'question_text']
        verbose_name = 'Assessment Question'
        verbose_name_plural = 'Assessment Questions'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['framework']),
        ]
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.question_text[:50]}"


class AssessmentTemplate(models.Model):
    """
    Predefined assessment templates with sets of questions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    framework = models.CharField(
        max_length=20,
        choices=AssessmentQuestion.FRAMEWORK_CHOICES,
        default='custom'
    )
    
    # Questions included in this template
    questions = models.ManyToManyField(
        AssessmentQuestion,
        related_name='templates',
        through='TemplateQuestion'
    )
    
    # Template configuration
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates'
    )
    
    class Meta:
        db_table = 'assessment_templates'
        ordering = ['name']
        verbose_name = 'Assessment Template'
        verbose_name_plural = 'Assessment Templates'
    
    def __str__(self):
        return self.name
    
    def get_question_count(self):
        """Return number of questions in template"""
        return self.questions.count()


class TemplateQuestion(models.Model):
    """
    Through model for AssessmentTemplate and AssessmentQuestion
    Allows customization of questions per template
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(AssessmentTemplate, on_delete=models.CASCADE)
    question = models.ForeignKey(AssessmentQuestion, on_delete=models.CASCADE)
    
    # Template-specific overrides
    order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=True)
    custom_guidance = models.TextField(blank=True)
    
    class Meta:
        db_table = 'template_questions'
        ordering = ['order']
        unique_together = ['template', 'question']


class AssessmentEvidence(models.Model):
    """
    Supporting evidence/documentation for assessment responses
    """
    EVIDENCE_TYPES = [
        ('document', 'Document'),
        ('screenshot', 'Screenshot'),
        ('certificate', 'Certificate'),
        ('report', 'Report'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        VendorAssessment,
        on_delete=models.CASCADE,
        related_name='evidence'
    )
    
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default='document')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # File attachment
    file = models.FileField(
        upload_to='assessment_evidence/',
        help_text="Upload supporting documentation"
    )
    
    # Link to specific question (optional)
    question_id = models.CharField(max_length=100, blank=True)
    
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_evidence'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'assessment_evidence'
        ordering = ['-uploaded_at']
        verbose_name = 'Assessment Evidence'
        verbose_name_plural = 'Assessment Evidence'
    
    def __str__(self):
        return f"{self.title} - {self.assessment}"