from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Q
from django.contrib.auth import get_user_model

from .models import Organization, UserProfile
from .serializers import (
    UserSerializer, UserListSerializer, UserProfileSerializer,
    OrganizationSerializer, OrganizationDetailSerializer,
    OrganizationStatsSerializer
)

User = get_user_model()
from drf_yasg.utils import swagger_auto_schema



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current authenticated user with profile"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@swagger_auto_schema(methods=['PUT', 'PATCH'], request_body=UserSerializer)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_current_user(request):
    """Update current user profile"""
    serializer = UserSerializer(
        request.user,
        data=request.data,
        partial=request.method == 'PATCH',
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """List all users in current user's organization"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if not hasattr(request.user, 'profile') or not profile.organization:
        return Response(
            {'error': 'User must be associated with an organization'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Only admin and managers can list all users
    if profile.role not in ['admin', 'manager']:
        return Response(
            {'error': 'Insufficient permissions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    organization = profile.organization
    users = User.objects.filter(profile__organization=organization)
    
    # Apply filters
    role = request.query_params.get('role')
    if role:
        users = users.filter(profile__role=role)
    
    is_active = request.query_params.get('is_active')
    if is_active is not None:
        users = users.filter(is_active=is_active.lower() == 'true')
    
    # Search
    search = request.query_params.get('search')
    if search:
        users = users.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    serializer = UserListSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_detail(request, user_id):
    """Get specific user details"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if not hasattr(request.user, 'profile'):
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = get_object_or_404(User, id=user_id)
    
    # Check if user can view this profile
    if request.user.id != user.id and profile.role not in ['admin', 'manager']:
        return Response(
            {'error': 'Insufficient permissions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = UserSerializer(user)
    return Response(serializer.data)


@swagger_auto_schema(methods=['PUT', 'PATCH'], request_body=UserSerializer)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    """Update user (admin only)"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if not hasattr(request.user, 'profile') or profile.role != 'admin':
        return Response(
            {'error': 'Admin permissions required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = get_object_or_404(User, id=user_id)
    
    serializer = UserSerializer(
        user,
        data=request.data,
        partial=request.method == 'PATCH',
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(methods=['PUT', 'PATCH'], request_body=UserProfileSerializer)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_user_profile(request, user_id):
    """Update user profile"""
    profile = get_object_or_404(UserProfile, user=request.user)
    user = get_object_or_404(User, id=user_id)
    
    # Can only update own profile or if admin
    if request.user.id != user.id and profile.role != 'admin':
        return Response(
            {'error': 'Insufficient permissions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not hasattr(user, 'profile'):
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = UserProfileSerializer(
        user.profile,
        data=request.data,
        partial=request.method == 'PATCH'
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_organization(request):
    """Get current user's organization"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if not hasattr(request.user, 'profile') or not profile.organization:
        return Response(
            {'error': 'User not associated with an organization'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    organization = profile.organization
    serializer = OrganizationDetailSerializer(organization)
    return Response(serializer.data)


@swagger_auto_schema(methods=['PUT', 'PATCH'], request_body=OrganizationSerializer)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_organization(request):
    """Update organization (admin only)"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if not hasattr(request.user, 'profile') or profile.role != 'admin':
        return Response(
            {'error': 'Admin permissions required'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not profile.organization:
        return Response(
            {'error': 'Organization not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    organization = profile.organization
    serializer = OrganizationSerializer(
        organization,
        data=request.data,
        partial=request.method == 'PATCH'
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(methods=['POST'], request_body=OrganizationSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_organization(request):
    """Create new organization (for onboarding)"""
    profile = get_object_or_404(UserProfile, user=request.user)
    # Check if user already has organization
    if hasattr(request.user, 'profile') and profile.organization:
        return Response(
            {'error': 'User already associated with an organization'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = OrganizationSerializer(data=request.data)
    
    if serializer.is_valid():
        organization = serializer.save()
        
        # Update or create user profile with this organization
        if hasattr(request.user, 'profile'):
            profile = profile
            profile.organization = organization
            profile.role = 'admin'  # Creator becomes admin
            profile.save()
        
        return Response(
            OrganizationDetailSerializer(organization).data,
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_organization_stats(request):
    """Get dashboard statistics for organization"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if not hasattr(request.user, 'profile') or not profile.organization:
        return Response(
            {'error': 'Organization not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    org = profile.organization
    
    # Import here to avoid circular imports
    from vendors.models import Vendor
    from simulations.models import Simulation
    from assessments.models import VendorAssessment
    from django.utils import timezone
    from datetime import timedelta
    
    # Calculate stats
    vendors = Vendor.objects.filter(organization=org)
    simulations = Simulation.objects.filter(organization=org)
    assessments = VendorAssessment.objects.filter(vendor__organization=org)
    
    # Recent assessments (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_assessments = assessments.filter(created_at__gte=thirty_days_ago).count()
    
    # Expiring certifications (next 90 days)
    from vendors.models import ComplianceCertification
    ninety_days_ahead = timezone.now().date() + timedelta(days=90)
    expiring_certifications = ComplianceCertification.objects.filter(
        vendor__organization=org,
        expiry_date__lte=ninety_days_ahead,
        is_active=True
    ).count()
    
    stats = {
        'total_vendors': vendors.count(),
        'high_risk_vendors': vendors.filter(risk_level__in=['high', 'critical']).count(),
        'total_simulations': simulations.count(),
        'completed_simulations': simulations.filter(status='completed').count(),
        'average_risk_score': vendors.aggregate(Avg('overall_risk_score'))['overall_risk_score__avg'] or 0,
        'vendors_by_risk_level': {
            'low': vendors.filter(risk_level='low').count(),
            'medium': vendors.filter(risk_level='medium').count(),
            'high': vendors.filter(risk_level='high').count(),
            'critical': vendors.filter(risk_level='critical').count(),
        },
        'recent_assessments': recent_assessments,
        'expiring_certifications': expiring_certifications,
    }
    
    serializer = OrganizationStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_overview(request):
    """Get comprehensive dashboard overview"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if not hasattr(request.user, 'profile') or not profile.organization:
        return Response(
            {'error': 'Organization not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    org = profile.organization
    
    from vendors.models import Vendor, IncidentHistory
    from simulations.models import Simulation, SimulationResult
    from assessments.models import VendorAssessment
    from vendors.serializers import VendorListSerializer
    from simulations.serializers import SimulationListSerializer
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    
    # Vendors
    vendors = Vendor.objects.filter(organization=org)
    high_risk_vendors = vendors.filter(risk_level__in=['high', 'critical']).order_by('-overall_risk_score')[:5]
    
    # Simulations
    recent_simulations = Simulation.objects.filter(
        organization=org,
        status='completed'
    ).order_by('-completed_at')[:5]
    
    # Total estimated impact from all simulations
    total_impact = SimulationResult.objects.filter(
        simulation__organization=org
    ).aggregate(total=models.Sum('total_financial_impact'))['total'] or Decimal('0')
    
    # Recent incidents (last 6 months)
    six_months_ago = timezone.now().date() - timedelta(days=180)
    recent_incidents = IncidentHistory.objects.filter(
        vendor__organization=org,
        incident_date__gte=six_months_ago
    ).count()
    
    # Pending assessments
    pending_assessments = VendorAssessment.objects.filter(
        vendor__organization=org,
        status__in=['draft', 'in_progress']
    ).count()
    
    overview = {
        'organization': OrganizationSerializer(org).data,
        'summary': {
            'total_vendors': vendors.count(),
            'active_vendors': vendors.filter(is_active=True).count(),
            'high_risk_vendors_count': vendors.filter(risk_level__in=['high', 'critical']).count(),
            'average_risk_score': vendors.aggregate(Avg('overall_risk_score'))['overall_risk_score__avg'] or 0,
            'total_simulations': Simulation.objects.filter(organization=org).count(),
            'total_estimated_impact': float(total_impact),
            'recent_incidents': recent_incidents,
            'pending_assessments': pending_assessments,
        },
        'high_risk_vendors': VendorListSerializer(high_risk_vendors, many=True).data,
        'recent_simulations': SimulationListSerializer(recent_simulations, many=True).data,
    }
    
    return Response(overview)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_permissions(request):
    """Get current user's permissions and role"""
    if not hasattr(request.user, 'profile'):
        return Response({
            'role': None,
            'organization': None,
            'permissions': {
                'can_create_vendors': False,
                'can_delete_vendors': False,
                'can_create_simulations': False,
                'can_manage_users': False,
                'can_approve_assessments': False,
            }
        })
    
    profile = get_object_or_404(UserProfile, user=request.user)
    role = profile.role
    
    permissions = {
        'role': role,
        'organization': OrganizationSerializer(profile.organization).data if profile.organization else None,
        'permissions': {
            'can_create_vendors': role in ['admin', 'analyst', 'manager'],
            'can_delete_vendors': role == 'admin',
            'can_create_simulations': profile.can_create_simulations,
            'can_manage_users': role in ['admin', 'manager'],
            'can_approve_assessments': role in ['admin', 'manager'],
            'can_edit_organization': role == 'admin',
        }
    }
    
    return Response(permissions)




from django.db import models