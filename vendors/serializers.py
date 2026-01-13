from rest_framework import serializers
from .models import Vendor, IncidentHistory, ComplianceCertification, VendorContact
from decimal import Decimal


class VendorContactSerializer(serializers.ModelSerializer):
    """Serializer for VendorContact"""
    
    class Meta:
        model = VendorContact
        fields = [
            'id', 'vendor', 'contact_type', 'name', 'title', 'email',
            'phone', 'is_primary', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ComplianceCertificationSerializer(serializers.ModelSerializer):
    """Serializer for ComplianceCertification"""
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    certification_type_display = serializers.CharField(
        source='get_certification_type_display',
        read_only=True
    )
    
    class Meta:
        model = ComplianceCertification
        fields = [
            'id', 'vendor', 'certification_type', 'certification_type_display',
            'certification_body', 'issue_date', 'expiry_date', 'is_active',
            'certificate_number', 'certificate_file', 'verification_url',
            'notes', 'is_expired', 'days_until_expiry', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_days_until_expiry(self, obj):
        return obj.days_until_expiry()


class IncidentHistorySerializer(serializers.ModelSerializer):
    """Serializer for IncidentHistory"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    incident_type_display = serializers.CharField(
        source='get_incident_type_display',
        read_only=True
    )
    severity_display = serializers.CharField(
        source='get_severity_display',
        read_only=True
    )
    total_response_time = serializers.FloatField(read_only=True)
    
    class Meta:
        model = IncidentHistory
        fields = [
            'id', 'vendor', 'vendor_name', 'incident_date', 'incident_type',
            'incident_type_display', 'severity', 'severity_display', 'title',
            'description', 'records_affected', 'downtime_hours', 'financial_impact',
            'time_to_detect_hours', 'time_to_contain_hours', 'time_to_recover_hours',
            'total_response_time', 'root_cause', 'lessons_learned',
            'remediation_actions', 'remediation_completed', 'publicly_disclosed',
            'disclosure_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VendorListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for vendor lists"""
    risk_level_display = serializers.CharField(
        source='get_risk_level_display',
        read_only=True
    )
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'industry', 'country', 'services_provided',
            'overall_risk_score', 'risk_level', 'risk_level_display',
            'contract_end_date', 'is_active', 'created_at'
        ]
        read_only_fields = fields


class VendorDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for vendor with all relationships"""
    certifications = ComplianceCertificationSerializer(many=True, read_only=True)
    incident_history = IncidentHistorySerializer(many=True, read_only=True)
    contacts = VendorContactSerializer(many=True, read_only=True)
    dependent_vendors = VendorListSerializer(many=True, read_only=True)
    dependency_of = VendorListSerializer(many=True, read_only=True)
    
    assessment_count = serializers.SerializerMethodField()
    simulation_count = serializers.SerializerMethodField()
    active_certification_count = serializers.SerializerMethodField()
    recent_incident_count = serializers.SerializerMethodField()
    
    risk_level_display = serializers.CharField(
        source='get_risk_level_display',
        read_only=True
    )
    
    class Meta:
        model = Vendor
        fields = '__all__'
        read_only_fields = [
            'id', 'overall_risk_score', 'risk_level', 'created_at', 'updated_at'
        ]
    
    def get_assessment_count(self, obj):
        return obj.assessments.count()
    
    def get_simulation_count(self, obj):
        return obj.simulations.count()
    
    def get_active_certification_count(self, obj):
        return obj.certifications.filter(is_active=True).count()
    
    def get_recent_incident_count(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        one_year_ago = timezone.now().date() - timedelta(days=365)
        return obj.incident_history.filter(incident_date__gte=one_year_ago).count()


class VendorCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating vendors"""
    
    class Meta:
        model = Vendor
        fields = [
            'name', 'industry', 'country', 'website', 'contact_name',
            'contact_email', 'contact_phone', 'services_provided',
            'contract_start_date', 'contract_end_date', 'contract_value',
            'security_posture_score', 'data_sensitivity_level',
            'service_criticality_level', 'incident_history_score',
            'compliance_score', 'third_party_dependencies_score',
            'dependent_vendors', 'is_active', 'notes'
        ]
    
    def validate_contract_value(self, value):
        """Validate contract value is positive"""
        if value < 0:
            raise serializers.ValidationError("Contract value must be positive")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        if 'contract_start_date' in data and 'contract_end_date' in data:
            if data['contract_end_date'] < data['contract_start_date']:
                raise serializers.ValidationError({
                    'contract_end_date': 'End date must be after start date'
                })
        return data
    
    def create(self, validated_data):
        """Create vendor and calculate risk score"""
        dependent_vendors = validated_data.pop('dependent_vendors', [])
        
        # Set organization from request context
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            validated_data['organization'] = request.user.profile.organization
            validated_data['created_by'] = request.user
        
        vendor = Vendor.objects.create(**validated_data)
        vendor.dependent_vendors.set(dependent_vendors)
        vendor.calculate_risk_score()
        
        return vendor
    
    def update(self, instance, validated_data):
        """Update vendor and recalculate risk score"""
        dependent_vendors = validated_data.pop('dependent_vendors', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if dependent_vendors is not None:
            instance.dependent_vendors.set(dependent_vendors)
        
        instance.calculate_risk_score()
        return instance


class VendorRiskScoreSerializer(serializers.Serializer):
    """Serializer for vendor risk score calculation"""
    vendor_id = serializers.UUIDField()
    vendor_name = serializers.CharField()
    overall_risk_score = serializers.FloatField()
    risk_level = serializers.CharField()
    
    # Component scores
    security_posture_score = serializers.IntegerField()
    data_sensitivity_level = serializers.IntegerField()
    service_criticality_level = serializers.IntegerField()
    incident_history_score = serializers.IntegerField()
    compliance_score = serializers.IntegerField()
    third_party_dependencies_score = serializers.IntegerField()
    
    # Metadata
    last_calculated = serializers.DateTimeField()


class VendorDependencySerializer(serializers.Serializer):
    """Serializer for vendor dependency information"""
    vendor_id = serializers.UUIDField()
    vendor_name = serializers.CharField()
    risk_level = serializers.CharField()
    
    depends_on = VendorListSerializer(many=True)
    depended_by = VendorListSerializer(many=True)
    
    dependency_chain = serializers.ListField(
        child=serializers.DictField()
    )


class VendorComparisonSerializer(serializers.Serializer):
    """Serializer for comparing multiple vendors"""
    vendors = VendorListSerializer(many=True)
    
    comparison_metrics = serializers.DictField(
        child=serializers.DictField()
    )
    
    risk_distribution = serializers.DictField()
    
    recommendations = serializers.ListField(
        child=serializers.CharField()
    )


class VendorSummarySerializer(serializers.Serializer):
    """Serializer for vendor portfolio summary"""
    total_vendors = serializers.IntegerField()
    active_vendors = serializers.IntegerField()
    inactive_vendors = serializers.IntegerField()
    
    by_risk_level = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    by_industry = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    average_risk_score = serializers.FloatField()
    total_contract_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    high_risk_vendors = VendorListSerializer(many=True)
    expiring_contracts = VendorListSerializer(many=True)


class IncidentTrendsSerializer(serializers.Serializer):
    """Serializer for incident trend analysis"""
    total_incidents = serializers.IntegerField()
    
    by_type = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    by_severity = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    total_financial_impact = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_downtime = serializers.FloatField()
    
    trends_over_time = serializers.ListField(
        child=serializers.DictField()
    )
    
    most_affected_vendors = serializers.ListField(
        child=serializers.DictField()
    )


class CertificationStatusSerializer(serializers.Serializer):
    """Serializer for certification status overview"""
    total_certifications = serializers.IntegerField()
    active_certifications = serializers.IntegerField()
    expired_certifications = serializers.IntegerField()
    
    expiring_soon = ComplianceCertificationSerializer(many=True)
    
    by_type = serializers.DictField(
        child=serializers.IntegerField()
    )
    
    vendors_without_certifications = VendorListSerializer(many=True)


class CompareVendorsSerializer(serializers.Serializer):
    """Serializer for comparing multiple vendors"""
    vendor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    