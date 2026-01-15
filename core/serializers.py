from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Organization, UserProfile

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'user_email', 'user_first_name', 'user_last_name',
            'organization', 'organization_name', 'role', 'phone', 'department',
            'job_title', 'preferences', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User with profile data"""
    profile = UserProfileSerializer(read_only=True)
    organization_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    role = serializers.CharField(write_only=True, required=False)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'is_verified',
            'is_active', 'created_at', 'profile',
            # Write-only fields for profile creation
            'organization_id', 'role', 'phone'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'email']
    

    def update(self, instance, validated_data):
        """Update user and profile"""
        organization_id = validated_data.pop('organization_id', None)
        role = validated_data.pop('role', None)
        phone = validated_data.pop('phone', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile
        
        profile = instance.get_or_create_profile()
        if organization_id is not None:
            profile.organization_id = organization_id
        if role is not None:
            profile.role = role
        if phone is not None:
            profile.phone = phone
        profile.save()
        
        return instance


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for user lists"""
    organization_name = serializers.CharField(source='profile.organization.name', read_only=True)
    role = serializers.CharField(source='profile.role', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'organization_name', 'role', 'is_active']
        read_only_fields = fields


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization"""
    user_count = serializers.SerializerMethodField()
    vendor_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'industry', 'size', 'country', 'config',
            'user_count', 'vendor_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_count(self, obj):
        return obj.user_profiles.count()
    
    def get_vendor_count(self, obj):
        return obj.vendors.count()


class OrganizationDetailSerializer(OrganizationSerializer):
    """Detailed organization serializer with related data"""
    users = UserListSerializer(source='user_profiles', many=True, read_only=True)
    
    class Meta(OrganizationSerializer.Meta):
        fields = OrganizationSerializer.Meta.fields + ['users']


class OrganizationStatsSerializer(serializers.Serializer):
    """Serializer for organization statistics"""
    total_vendors = serializers.IntegerField()
    high_risk_vendors = serializers.IntegerField()
    total_simulations = serializers.IntegerField()
    completed_simulations = serializers.IntegerField()
    average_risk_score = serializers.FloatField()
    vendors_by_risk_level = serializers.DictField()
    recent_assessments = serializers.IntegerField()
    expiring_certifications = serializers.IntegerField()

