from rest_framework import serializers
from .models import (
    VendorAssessment, AssessmentQuestion, AssessmentTemplate,
    TemplateQuestion, AssessmentEvidence
)


class AssessmentEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for AssessmentEvidence"""
    uploaded_by_name = serializers.CharField(
        source='uploaded_by.get_full_name',
        read_only=True
    )
    evidence_type_display = serializers.CharField(
        source='get_evidence_type_display',
        read_only=True
    )
    
    class Meta:
        model = AssessmentEvidence
        fields = [
            'id', 'assessment', 'evidence_type', 'evidence_type_display',
            'title', 'description', 'file', 'question_id',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    """Serializer for AssessmentQuestion"""
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    framework_display = serializers.CharField(
        source='get_framework_display',
        read_only=True
    )
    response_type_display = serializers.CharField(
        source='get_response_type_display',
        read_only=True
    )
    
    class Meta:
        model = AssessmentQuestion
        fields = [
            'id', 'category', 'category_display', 'framework',
            'framework_display', 'question_text', 'guidance',
            'response_type', 'response_type_display', 'response_options',
            'weight', 'max_score', 'is_required', 'is_active', 'order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TemplateQuestionSerializer(serializers.ModelSerializer):
    """Serializer for TemplateQuestion"""
    question = AssessmentQuestionSerializer(read_only=True)
    question_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = TemplateQuestion
        fields = [
            'id', 'template', 'question', 'question_id',
            'order', 'is_required', 'custom_guidance'
        ]
        read_only_fields = ['id']


class AssessmentTemplateSerializer(serializers.ModelSerializer):
    """Serializer for AssessmentTemplate"""
    question_count = serializers.SerializerMethodField()
    framework_display = serializers.CharField(
        source='get_framework_display',
        read_only=True
    )
    
    class Meta:
        model = AssessmentTemplate
        fields = [
            'id', 'name', 'description', 'framework', 'framework_display',
            'is_default', 'is_active', 'question_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_question_count(self, obj):
        return obj.get_question_count()


class AssessmentTemplateDetailSerializer(AssessmentTemplateSerializer):
    """Detailed template serializer with questions"""
    template_questions = TemplateQuestionSerializer(
        source='templatequestion_set',
        many=True,
        read_only=True
    )
    
    class Meta(AssessmentTemplateSerializer.Meta):
        fields = AssessmentTemplateSerializer.Meta.fields + ['template_questions']


class VendorAssessmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for assessment lists"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    assessed_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    assessment_type_display = serializers.CharField(
        source='get_assessment_type_display',
        read_only=True
    )
    
    class Meta:
        model = VendorAssessment
        fields = [
            'id', 'vendor', 'vendor_name', 'assessment_date',
            'assessment_type', 'assessment_type_display',
            'status', 'status_display', 'overall_score',
            'assessed_by', 'assessed_by_name', 'created_at'
        ]
        read_only_fields = fields
    
    def get_assessed_by_name(self, obj):
        if obj.assessed_by:
            return f"{obj.assessed_by.first_name} {obj.assessed_by.last_name}".strip()
        return None


class VendorAssessmentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for vendor assessment"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    assessed_by_name = serializers.SerializerMethodField()
    evidence = AssessmentEvidenceSerializer(many=True, read_only=True)
    score_breakdown = serializers.SerializerMethodField()
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    assessment_type_display = serializers.CharField(
        source='get_assessment_type_display',
        read_only=True
    )
    
    class Meta:
        model = VendorAssessment
        fields = [
            'id', 'vendor', 'vendor_name', 'assessed_by', 'assessed_by_name',
            'assessment_date', 'assessment_type', 'assessment_type_display',
            'responses', 'access_control_score', 'data_protection_score',
            'network_security_score', 'incident_response_score',
            'vulnerability_management_score', 'business_continuity_score',
            'security_governance_score', 'overall_score', 'score_breakdown',
            'status', 'status_display', 'notes', 'findings', 'recommendations',
            'requires_followup', 'followup_date', 'followup_completed',
            'evidence', 'approved_by', 'approved_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'assessment_date', 'overall_score', 'created_at', 'updated_at'
        ]
    
    def get_assessed_by_name(self, obj):
        if obj.assessed_by:
            return f"{obj.assessed_by.first_name} {obj.assessed_by.last_name}".strip()
        return None
    
    def get_score_breakdown(self, obj):
        return obj.get_score_breakdown()


class VendorAssessmentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating assessments"""
    
    class Meta:
        model = VendorAssessment
        fields = [
            'vendor', 'assessment_type', 'responses',
            'access_control_score', 'data_protection_score',
            'network_security_score', 'incident_response_score',
            'vulnerability_management_score', 'business_continuity_score',
            'security_governance_score', 'status', 'notes', 'findings',
            'recommendations', 'requires_followup', 'followup_date'
        ]
    
    def validate(self, data):
        """Validate assessment data"""
        # Ensure all scores are between 0-100
        score_fields = [
            'access_control_score', 'data_protection_score',
            'network_security_score', 'incident_response_score',
            'vulnerability_management_score', 'business_continuity_score',
            'security_governance_score'
        ]
        
        for field in score_fields:
            if field in data:
                score = data[field]
                if not 0 <= score <= 100:
                    raise serializers.ValidationError({
                        field: f"Score must be between 0 and 100"
                    })
        
        # If requires followup, ensure followup_date is set
        if data.get('requires_followup') and not data.get('followup_date'):
            raise serializers.ValidationError({
                'followup_date': 'Follow-up date is required when follow-up is needed'
            })
        
        return data
    
    def create(self, validated_data):
        """Create assessment and calculate overall score"""
        request = self.context.get('request')
        if request:
            validated_data['assessed_by'] = request.user
        
        assessment = VendorAssessment.objects.create(**validated_data)
        assessment.calculate_overall_score()
        
        return assessment
    
    def update(self, instance, validated_data):
        """Update assessment and recalculate score"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.calculate_overall_score()
        
        return instance


class AssessmentComparisonSerializer(serializers.Serializer):
    """Serializer for comparing assessments"""
    current = serializers.DictField()
    previous = serializers.DictField()
    changes = serializers.DictField()
    improvement_percentage = serializers.FloatField()
    trend = serializers.CharField()  # 'improving', 'declining', 'stable'


class AssessmentQuestionnaireResponseSerializer(serializers.Serializer):
    """Serializer for questionnaire responses"""
    question_id = serializers.UUIDField()
    question_text = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    response_type = serializers.CharField(read_only=True)
    response = serializers.JSONField()
    score = serializers.IntegerField(min_value=0, max_value=100)
    notes = serializers.CharField(required=False, allow_blank=True)
    evidence_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )


class AssessmentTemplateQuestionnaireSerializer(serializers.Serializer):
    """Serializer for complete questionnaire from template"""
    template_id = serializers.UUIDField()
    template_name = serializers.CharField()
    categories = serializers.ListField(
        child=serializers.DictField()
    )
    total_questions = serializers.IntegerField()


class AssessmentSummarySerializer(serializers.Serializer):
    """Serializer for assessment portfolio summary"""
    total_assessments = serializers.IntegerField()
    completed_assessments = serializers.IntegerField()
    pending_assessments = serializers.IntegerField()
    
    average_score = serializers.FloatField()
    
    by_status = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    recent_assessments = VendorAssessmentListSerializer(many=True)
    vendors_needing_assessment = serializers.ListField(
        child=serializers.DictField()
    )
    
    score_trends = serializers.ListField(
        child=serializers.DictField()
    )


class AssessmentApprovalSerializer(serializers.Serializer):
    """Serializer for assessment approval"""
    assessment_id = serializers.UUIDField()
    approval_notes = serializers.CharField(required=False, allow_blank=True)
    approved = serializers.BooleanField()


class BulkAssessmentCreateSerializer(serializers.Serializer):
    """Serializer for creating multiple assessments at once"""
    vendor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    template_id = serializers.UUIDField()
    assessment_type = serializers.ChoiceField(
        choices=VendorAssessment._meta.get_field('assessment_type').choices
    )
    scheduled_date = serializers.DateField(required=False)


class AssessmentScheduleSerializer(serializers.Serializer):
    """Serializer for assessment scheduling"""
    vendor_id = serializers.UUIDField()
    assessment_type = serializers.ChoiceField(
        choices=VendorAssessment._meta.get_field('assessment_type').choices
    )
    scheduled_date = serializers.DateField()
    assigned_to = serializers.UUIDField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)