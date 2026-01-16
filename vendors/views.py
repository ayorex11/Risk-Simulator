from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Vendor, IncidentHistory, ComplianceCertification, VendorContact
from .serializers import (
    VendorListSerializer, VendorDetailSerializer, VendorCreateUpdateSerializer,
    VendorRiskScoreSerializer, VendorDependencySerializer, VendorComparisonSerializer,
    VendorSummarySerializer, IncidentHistorySerializer, IncidentTrendsSerializer,
    ComplianceCertificationSerializer, CertificationStatusSerializer,
    VendorContactSerializer, CompareVendorsSerializer
)
from core.models import UserProfile
from drf_yasg.utils import swagger_auto_schema


@swagger_auto_schema(methods=['POST'], request_body=VendorCreateUpdateSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser])
def vendor_list_create(request):
    """List all vendors or create new vendor"""
    profile = request.user.profile
    
    if not profile.organization:
        return Response(
            {'error': 'User must be associated with an organization'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    organization = profile.organization
    
    if request.method == 'GET':
        vendors = Vendor.objects.filter(organization=organization)
        
        # Apply filters
        risk_level = request.query_params.get('risk_level')
        if risk_level:
            vendors = vendors.filter(risk_level=risk_level)
        
        industry = request.query_params.get('industry')
        if industry:
            vendors = vendors.filter(industry__icontains=industry)
        
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            vendors = vendors.filter(is_active=is_active.lower() == 'true')
        
        # Search
        search = request.query_params.get('search')
        if search:
            vendors = vendors.filter(
                Q(name__icontains=search) |
                Q(services_provided__icontains=search) |
                Q(industry__icontains=search)
            )
        
        # Ordering
        ordering = request.query_params.get('ordering', '-overall_risk_score')
        vendors = vendors.order_by(ordering)
        
        serializer = VendorListSerializer(vendors, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Check permissions
        if profile.role not in ['admin', 'analyst', 'manager']:
            return Response(
                {'error': 'Insufficient permissions to create vendors'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = VendorCreateUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            vendor = serializer.save()
            return Response(
                VendorDetailSerializer(vendor).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(methods=['PUT', 'PATCH'], request_body=VendorCreateUpdateSerializer)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser])
def vendor_detail(request, vendor_id):
    """Get, update, or delete a vendor"""
    profile = request.user.profile
    
    if not profile.organization:
        return Response(
            {'error': 'User must be associated with an organization'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    vendor = get_object_or_404(
        Vendor,
        id=vendor_id,
        organization= profile.organization
    )
    
    if request.method == 'GET':
        serializer = VendorDetailSerializer(vendor)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        # Check permissions
        if profile.role not in ['admin', 'analyst', 'manager']:
            return Response(
                {'error': 'Insufficient permissions to update vendors'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = VendorCreateUpdateSerializer(
            vendor,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        
        if serializer.is_valid():
            vendor = serializer.save()
            return Response(VendorDetailSerializer(vendor).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admins can delete
        if profile.role != 'admin':
            return Response(
                {'error': 'Admin permissions required to delete vendors'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vendor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser])
def recalculate_vendor_risk(request, vendor_id):
    """Manually recalculate vendor risk score"""
    profile = request.user.profile
    
    vendor = get_object_or_404(
        Vendor,
        id=vendor_id,
        organization= profile.organization
    )
    
    new_score = vendor.calculate_risk_score()
    
    return Response({
        'message': 'Risk score recalculated successfully',
        'vendor_id': str(vendor.id),
        'vendor_name': vendor.name,
        'overall_risk_score': new_score,
        'risk_level': vendor.risk_level
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_risk_history(request, vendor_id):
    """Get risk score history from assessments"""
    profile = request.user.profile
    
    vendor = get_object_or_404(
        Vendor,
        id=vendor_id,
        organization= profile.organization
    )
    
    from assessments.models import VendorAssessment
    
    assessments = VendorAssessment.objects.filter(
        vendor=vendor,
        status='completed'
    ).order_by('-assessment_date')[:12]
    
    history = [{
        'date': assessment.assessment_date,
        'overall_score': assessment.overall_score,
        'vendor_risk_score': vendor.overall_risk_score,
        'assessed_by': f"{assessment.assessed_by.first_name} {assessment.assessed_by.last_name}" if assessment.assessed_by else None
    } for assessment in assessments]
    
    return Response({
        'vendor_id': str(vendor.id),
        'vendor_name': vendor.name,
        'current_risk_score': vendor.overall_risk_score,
        'current_risk_level': vendor.risk_level,
        'history': history
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_dependencies(request, vendor_id):
    """Get vendor dependency graph"""
    profile = request.user.profile
    
    vendor = get_object_or_404(
        Vendor,
        id=vendor_id,
        organization= profile.organization
    )
    
    # Get dependency chain
    dependency_chain = vendor.get_dependency_chain(max_depth=3)
    
    dependencies = {
        'vendor_id': str(vendor.id),
        'vendor_name': vendor.name,
        'risk_level': vendor.risk_level,
        'depends_on': VendorListSerializer(vendor.dependent_vendors.all(), many=True).data,
        'depended_by': VendorListSerializer(vendor.dependency_of.all(), many=True).data,
        'dependency_chain': [
            {
                'vendor_id': str(v.id),
                'vendor_name': v.name,
                'risk_level': v.risk_level,
                'depth': depth
            }
            for v, depth in dependency_chain
        ]
    }
    
    return Response(dependencies)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_summary(request):
    """Get vendor portfolio summary"""
    profile = request.user.profile
    
    if not profile.organization:
        return Response(
            {'error': 'Organization not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    org = profile.organization
    vendors = Vendor.objects.filter(organization=org)
    
    # Calculate summary stats
    high_risk_vendors = vendors.filter(risk_level__in=['high', 'critical']).order_by('-overall_risk_score')[:10]
    
    # Expiring contracts (next 90 days)
    ninety_days = timezone.now().date() + timedelta(days=90)
    expiring_contracts = vendors.filter(
        contract_end_date__lte=ninety_days,
        contract_end_date__gte=timezone.now().date()
    ).order_by('contract_end_date')[:10]
    
    # Group by industry
    by_industry = {}
    for vendor in vendors:
        industry = vendor.industry or 'Unknown'
        by_industry[industry] = by_industry.get(industry, 0) + 1
    
    summary = {
        'total_vendors': vendors.count(),
        'active_vendors': vendors.filter(is_active=True).count(),
        'inactive_vendors': vendors.filter(is_active=False).count(),
        'by_risk_level': {
            'low': vendors.filter(risk_level='low').count(),
            'medium': vendors.filter(risk_level='medium').count(),
            'high': vendors.filter(risk_level='high').count(),
            'critical': vendors.filter(risk_level='critical').count(),
        },
        'by_industry': by_industry,
        'average_risk_score': vendors.aggregate(Avg('overall_risk_score'))['overall_risk_score__avg'] or 0,
        'total_contract_value': vendors.aggregate(Sum('contract_value'))['contract_value__sum'] or Decimal('0'),
        'high_risk_vendors': VendorListSerializer(high_risk_vendors, many=True).data,
        'expiring_contracts': VendorListSerializer(expiring_contracts, many=True).data,
    }
    
    serializer = VendorSummarySerializer(summary)
    return Response(serializer.data)


@swagger_auto_schema(methods=['POST'], request_body=CompareVendorsSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser])
def compare_vendors(request):
    """Compare multiple vendors"""
    profile = request.user.profile
    
    serializer = CompareVendorsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    vendor_ids = serializer.validated_data['vendor_ids']
    
    if len(vendor_ids) < 2:
        return Response(
            {'error': 'At least 2 vendors required for comparison'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    vendors = Vendor.objects.filter(
        id__in=vendor_ids,
        organization= profile.organization
    )
    
    if vendors.count() != len(vendor_ids):
        return Response(
            {'error': 'One or more vendors not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Build comparison metrics
    comparison_metrics = {}
    for vendor in vendors:
        comparison_metrics[str(vendor.id)] = {
            'name': vendor.name,
            'overall_risk_score': float(vendor.overall_risk_score),
            'risk_level': vendor.risk_level,
            'security_posture_score': vendor.security_posture_score,
            'data_sensitivity_level': vendor.data_sensitivity_level,
            'service_criticality_level': vendor.service_criticality_level,
            'compliance_score': vendor.compliance_score,
            'incident_count': vendor.incident_history.count(),
            'certification_count': vendor.certifications.filter(is_active=True).count(),
            'contract_value': float(vendor.contract_value),
        }
    
    # Risk distribution
    risk_distribution = {
        'low': vendors.filter(risk_level='low').count(),
        'medium': vendors.filter(risk_level='medium').count(),
        'high': vendors.filter(risk_level='high').count(),
        'critical': vendors.filter(risk_level='critical').count(),
    }
    
    # Recommendations
    recommendations = []
    highest_risk = vendors.order_by('-overall_risk_score').first()
    lowest_risk = vendors.order_by('overall_risk_score').first()
    
    if highest_risk.overall_risk_score > 75:
        recommendations.append(f"{highest_risk.name} has critical risk level - immediate action required")
    
    if lowest_risk.overall_risk_score < 25:
        recommendations.append(f"{lowest_risk.name} demonstrates excellent security posture")
    
    comparison = {
        'vendors': VendorListSerializer(vendors, many=True).data,
        'comparison_metrics': comparison_metrics,
        'risk_distribution': risk_distribution,
        'recommendations': recommendations,
    }
    
    return Response(comparison)



@swagger_auto_schema(methods=['POST'], request_body=IncidentHistorySerializer)
@api_view(['GET', 'POST'])
@parser_classes([FormParser, MultiPartParser])
@permission_classes([IsAuthenticated])
def incident_list_create(request):
    """List incidents or create new incident"""
    profile = request.user.profile
    
    if not profile.organization:
        return Response(
            {'error': 'Organization not found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.method == 'GET':
        vendor_id = request.query_params.get('vendor_id')
        incident_type = request.query_params.get('incident_type')
        severity = request.query_params.get('severity')
        
        # Get all incidents for organization's vendors
        vendor_ids = Vendor.objects.filter(
            organization= profile.organization
        ).values_list('id', flat=True)
        
        incidents = IncidentHistory.objects.filter(vendor_id__in=vendor_ids)
        
        # Apply filters
        if vendor_id:
            incidents = incidents.filter(vendor_id=vendor_id)
        if incident_type:
            incidents = incidents.filter(incident_type=incident_type)
        if severity:
            incidents = incidents.filter(severity=severity)
        
        # Ordering
        incidents = incidents.order_by('-incident_date')
        
        serializer = IncidentHistorySerializer(incidents, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = IncidentHistorySerializer(data=request.data)
        
        if serializer.is_valid():
            # Verify vendor belongs to organization
            vendor = serializer.validated_data['vendor']
            if vendor.organization != profile.organization:
                return Response(
                    {'error': 'Vendor does not belong to your organization'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            incident = serializer.save(reported_by=request.user)
            
            # Update vendor incident history score
            vendor.incident_history_score = max(0, vendor.incident_history_score - 5)
            vendor.calculate_risk_score()
            
            return Response(
                IncidentHistorySerializer(incident).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(methods=['PUT', 'PATCH'], request_body=IncidentHistorySerializer)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser])
def incident_detail(request, incident_id):
    """Get, update, or delete an incident"""
    profile = request.user.profile
    
    incident = get_object_or_404(IncidentHistory, id=incident_id)
    
    # Verify vendor belongs to organization
    if incident.vendor.organization != profile.organization:
        return Response(
            {'error': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = IncidentHistorySerializer(incident)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        serializer = IncidentHistorySerializer(
            incident,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if profile.role != 'admin':
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        incident.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def incident_trends(request):
    """Get incident trend analysis"""
    profile = request.user.profile
    
    org = profile.organization
    vendor_ids = Vendor.objects.filter(organization=org).values_list('id', flat=True)
    incidents = IncidentHistory.objects.filter(vendor_id__in=vendor_ids)
    
    # Group by type
    by_type = {}
    for incident_type, _ in IncidentHistory.INCIDENT_TYPES:
        count = incidents.filter(incident_type=incident_type).count()
        if count > 0:
            by_type[incident_type] = count
    
    # Group by severity
    by_severity = {}
    for severity, _ in IncidentHistory.SEVERITY_CHOICES:
        count = incidents.filter(severity=severity).count()
        if count > 0:
            by_severity[severity] = count
    
    # Most affected vendors
    from django.db.models import Count
    most_affected = incidents.values('vendor__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    trends = {
        'total_incidents': incidents.count(),
        'by_type': by_type,
        'by_severity': by_severity,
        'total_financial_impact': incidents.aggregate(Sum('financial_impact'))['financial_impact__sum'] or Decimal('0'),
        'average_downtime': incidents.aggregate(Avg('downtime_hours'))['downtime_hours__avg'] or 0,
        'trends_over_time': [],  # Could add monthly/quarterly breakdown
        'most_affected_vendors': list(most_affected),
    }
    
    serializer = IncidentTrendsSerializer(trends)
    return Response(serializer.data)



@swagger_auto_schema(methods=['POST'], request_body=ComplianceCertificationSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser])
def certification_list_create(request):
    """List certifications or create new certification"""
    profile = request.user.profile
    
    if request.method == 'GET':
        vendor_id = request.query_params.get('vendor_id')
        certification_type = request.query_params.get('certification_type')
        is_active = request.query_params.get('is_active')
        
        vendor_ids = Vendor.objects.filter(
            organization= profile.organization
        ).values_list('id', flat=True)
        
        certifications = ComplianceCertification.objects.filter(vendor_id__in=vendor_ids)
        
        if vendor_id:
            certifications = certifications.filter(vendor_id=vendor_id)
        if certification_type:
            certifications = certifications.filter(certification_type=certification_type)
        if is_active is not None:
            certifications = certifications.filter(is_active=is_active.lower() == 'true')
        
        certifications = certifications.order_by('-expiry_date')
        
        serializer = ComplianceCertificationSerializer(certifications, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = ComplianceCertificationSerializer(data=request.data)
        
        if serializer.is_valid():
            vendor = serializer.validated_data['vendor']
            if vendor.organization != profile.organization:
                return Response(
                    {'error': 'Vendor does not belong to your organization'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            certification = serializer.save(verified_by=request.user)
            
            # Update vendor compliance score
            active_certs = vendor.certifications.filter(is_active=True).count()
            vendor.compliance_score = min(50, active_certs * 10)
            vendor.calculate_risk_score()
            
            return Response(
                ComplianceCertificationSerializer(certification).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def certification_expiring_soon(request):
    """Get certifications expiring within 90 days"""
    profile = request.user.profile
    
    ninety_days = timezone.now().date() + timedelta(days=90)
    
    vendor_ids = Vendor.objects.filter(
        organization= profile.organization
    ).values_list('id', flat=True)
    
    expiring = ComplianceCertification.objects.filter(
        vendor_id__in=vendor_ids,
        expiry_date__lte=ninety_days,
        expiry_date__gte=timezone.now().date(),
        is_active=True
    ).order_by('expiry_date')
    
    serializer = ComplianceCertificationSerializer(expiring, many=True)
    return Response(serializer.data)



@swagger_auto_schema(methods=['POST'], request_body=VendorContactSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([FormParser, MultiPartParser])
def vendor_contact_list_create(request, vendor_id):
    """List or create vendor contacts"""
    profile = request.user.profile
    
    vendor = get_object_or_404(
        Vendor,
        id=vendor_id,
        organization= profile.organization
    )
    
    if request.method == 'GET':
        contacts = VendorContact.objects.filter(vendor=vendor)
        serializer = VendorContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = VendorContactSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(vendor=vendor)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)