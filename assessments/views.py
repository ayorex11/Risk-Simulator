from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count
from django.utils import timezone
from datetime import timedelta
from core.models import UserProfile
from .models import (
    VendorAssessment, AssessmentQuestion, AssessmentTemplate,
    TemplateQuestion, AssessmentEvidence
)
from vendors.models import Vendor
from .serializers import (
    VendorAssessmentListSerializer, VendorAssessmentDetailSerializer,
    VendorAssessmentCreateUpdateSerializer, AssessmentComparisonSerializer,
    AssessmentQuestionSerializer, AssessmentTemplateSerializer,
    AssessmentTemplateDetailSerializer, AssessmentEvidenceSerializer,
    AssessmentSummarySerializer, AssessmentQuestionnaireResponseSerializer,
    AssessmentApprovalSerializer
)
from drf_yasg.utils import swagger_auto_schema
@swagger_auto_schema(methods=['POST'], request_body=VendorAssessmentCreateUpdateSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def assessment_list_create(request):
    """List assessments or create new assessment"""
    profile = request.user.profile 
    if not profile.organization:
        return Response(
            {'error': 'Organization not found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.method == 'GET':
        # Get assessments for organization's vendors
        vendor_ids = Vendor.objects.filter(
            organization= profile.organization
        ).values_list('id', flat=True)
        
        assessments = VendorAssessment.objects.filter(vendor_id__in=vendor_ids)
        
        # Apply filters
        vendor_id = request.query_params.get('vendor_id')
        if vendor_id:
            assessments = assessments.filter(vendor_id=vendor_id)
        
        assessment_status = request.query_params.get('status')
        if assessment_status:
            assessments = assessments.filter(status=assessment_status)
        
        assessment_type = request.query_params.get('assessment_type')
        if assessment_type:
            assessments = assessments.filter(assessment_type=assessment_type)
        
        # Ordering
        assessments = assessments.order_by('-assessment_date')
        
        serializer = VendorAssessmentListSerializer(assessments, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Check permissions
        if profile.role not in ['admin', 'analyst', 'manager']:
            return Response(
                {'error': 'Insufficient permissions to create assessments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = VendorAssessmentCreateUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Verify vendor belongs to organization
            vendor = serializer.validated_data['vendor']
            if vendor.organization != profile.organization:
                return Response(
                    {'error': 'Vendor does not belong to your organization'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            assessment = serializer.save()
            return Response(
                VendorAssessmentDetailSerializer(assessment).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(methods=['PUT', 'PATCH'], request_body=VendorAssessmentCreateUpdateSerializer)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def assessment_detail(request, assessment_id):
    """Get, update, or delete an assessment"""
    profile = request.user.profile
    assessment = get_object_or_404(VendorAssessment, id=assessment_id)
    
    # Verify vendor belongs to organization
    if assessment.vendor.organization != profile.organization:
        return Response(
            {'error': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = VendorAssessmentDetailSerializer(assessment)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        # Can only update draft or in_progress assessments
        if assessment.status in ['completed', 'approved']:
            return Response(
                {'error': 'Cannot update completed or approved assessments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = VendorAssessmentCreateUpdateSerializer(
            assessment,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        
        if serializer.is_valid():
            assessment = serializer.save()
            return Response(VendorAssessmentDetailSerializer(assessment).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admins can delete
        if profile.role != 'admin':
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Can only delete draft assessments
        if assessment.status != 'draft':
            return Response(
                {'error': 'Can only delete draft assessments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assessment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_assessment(request, assessment_id):
    """Approve an assessment"""
    profile = request.user.profile
    
    if profile.role not in ['admin', 'manager']:
        return Response(
            {'error': 'Only admins and managers can approve assessments'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    assessment = get_object_or_404(VendorAssessment, id=assessment_id)
    
    if assessment.vendor.organization != profile.organization:
        return Response(
            {'error': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if assessment.status != 'completed':
        return Response(
            {'error': 'Only completed assessments can be approved'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    assessment.status = 'approved'
    assessment.approved_by = request.user
    assessment.approved_at = timezone.now()
    assessment.save()
    
    return Response({
        'message': 'Assessment approved successfully',
        'assessment': VendorAssessmentDetailSerializer(assessment).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def compare_assessments(request, assessment_id):
    """Compare assessment with previous assessment for same vendor"""
    profile = request.user.profile
    current = get_object_or_404(VendorAssessment, id=assessment_id)
    
    if current.vendor.organization != profile.organization:
        return Response(
            {'error': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Find previous assessment
    previous = VendorAssessment.objects.filter(
        vendor=current.vendor,
        assessment_date__lt=current.assessment_date,
        status__in=['completed', 'approved']
    ).order_by('-assessment_date').first()
    
    if not previous:
        return Response({
            'message': 'No previous assessment found for comparison',
            'current': VendorAssessmentDetailSerializer(current).data
        })
    
    # Calculate changes
    changes = {
        'overall': current.overall_score - previous.overall_score,
        'access_control': current.access_control_score - previous.access_control_score,
        'data_protection': current.data_protection_score - previous.data_protection_score,
        'network_security': current.network_security_score - previous.network_security_score,
        'incident_response': current.incident_response_score - previous.incident_response_score,
        'vulnerability_management': current.vulnerability_management_score - previous.vulnerability_management_score,
        'business_continuity': current.business_continuity_score - previous.business_continuity_score,
        'security_governance': current.security_governance_score - previous.security_governance_score,
    }
    
    # Calculate improvement percentage
    if previous.overall_score > 0:
        improvement_percentage = ((current.overall_score - previous.overall_score) / previous.overall_score) * 100
    else:
        improvement_percentage = 0
    
    # Determine trend
    if improvement_percentage > 5:
        trend = 'improving'
    elif improvement_percentage < -5:
        trend = 'declining'
    else:
        trend = 'stable'
    
    comparison = {
        'current': {
            'date': current.assessment_date,
            'overall_score': current.overall_score,
            'category_scores': current.get_score_breakdown()
        },
        'previous': {
            'date': previous.assessment_date,
            'overall_score': previous.overall_score,
            'category_scores': previous.get_score_breakdown()
        },
        'changes': changes,
        'improvement_percentage': improvement_percentage,
        'trend': trend
    }
    
    serializer = AssessmentComparisonSerializer(comparison)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assessment_summary(request):
    """Get assessment portfolio summary"""
    profile = request.user.profile
    
    org = profile.organization
    vendor_ids = Vendor.objects.filter(organization=org).values_list('id', flat=True)
    assessments = VendorAssessment.objects.filter(vendor_id__in=vendor_ids)
    
    # Recent assessments (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent = assessments.filter(created_at__gte=thirty_days_ago).order_by('-created_at')[:10]
    
    # Vendors needing assessment
    all_vendors = Vendor.objects.filter(organization=org, is_active=True)
    assessed_vendor_ids = assessments.values_list('vendor_id', flat=True).distinct()
    vendors_needing_assessment = all_vendors.exclude(id__in=assessed_vendor_ids)
    
    # Also include vendors whose last assessment is > 1 year old
    one_year_ago = timezone.now().date() - timedelta(days=365)
    for vendor in all_vendors:
        last_assessment = assessments.filter(vendor=vendor).order_by('-assessment_date').first()
        if last_assessment and last_assessment.assessment_date < one_year_ago:
            vendors_needing_assessment = vendors_needing_assessment | all_vendors.filter(id=vendor.id)
    
    # Status breakdown
    by_status = {}
    for status_choice, _ in VendorAssessment._meta.get_field('status').choices:
        count = assessments.filter(status=status_choice).count()
        if count > 0:
            by_status[status_choice] = count
    
    summary = {
        'total_assessments': assessments.count(),
        'completed_assessments': assessments.filter(status__in=['completed', 'approved']).count(),
        'pending_assessments': assessments.filter(status__in=['draft', 'in_progress']).count(),
        'average_score': assessments.filter(status__in=['completed', 'approved']).aggregate(
            Avg('overall_score')
        )['overall_score__avg'] or 0,
        'by_status': by_status,
        'recent_assessments': VendorAssessmentListSerializer(recent, many=True).data,
        'vendors_needing_assessment': [
            {'id': str(v.id), 'name': v.name, 'risk_level': v.risk_level}
            for v in vendors_needing_assessment[:10]
        ],
        'score_trends': []  # Could add monthly trends
    }
    
    serializer = AssessmentSummarySerializer(summary)
    return Response(serializer.data)


@swagger_auto_schema(methods=['POST'], request_body=AssessmentQuestionSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def question_list_create(request):
    """List questions or create new question (admin only)"""
    profile = request.user.profile
    
    if request.method == 'GET':
        questions = AssessmentQuestion.objects.filter(is_active=True)
        
        # Apply filters
        category = request.query_params.get('category')
        if category:
            questions = questions.filter(category=category)
        
        framework = request.query_params.get('framework')
        if framework:
            questions = questions.filter(framework=framework)
        
        questions = questions.order_by('category', 'order')
        
        serializer = AssessmentQuestionSerializer(questions, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        if profile.role != 'admin':
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AssessmentQuestionSerializer(data=request.data)
        
        if serializer.is_valid():
            question = serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_questionnaire_template(request):
    """Get assessment questionnaire template"""
    
    template_id = request.query_params.get('template_id')
    
    if template_id:
        template = get_object_or_404(AssessmentTemplate, id=template_id, is_active=True)
        questions = template.questions.filter(is_active=True).order_by('templatequestion__order')
    else:
        # Get all active questions
        questions = AssessmentQuestion.objects.filter(is_active=True).order_by('category', 'order')
    
    # Group by category
    categories = {}
    for question in questions:
        category = question.get_category_display()
        if category not in categories:
            categories[category] = {
                'name': category,
                'questions': []
            }
        
        categories[category]['questions'].append({
            'id': str(question.id),
            'question_text': question.question_text,
            'guidance': question.guidance,
            'response_type': question.response_type,
            'response_options': question.response_options,
            'is_required': question.is_required,
            'weight': question.weight,
            'max_score': question.max_score
        })
    
    return Response({
        'template_id': str(template_id) if template_id else None,
        'template_name': template.name if template_id else 'Default Questionnaire',
        'categories': list(categories.values()),
        'total_questions': questions.count()
    })



@swagger_auto_schema(methods=['POST'], request_body=AssessmentTemplateSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def template_list_create(request):
    """List templates or create new template (admin only)"""
    profile = get_object_or_404(UserProfile, user = request.user)
    
    if request.method == 'GET':
        templates = AssessmentTemplate.objects.filter(is_active=True)
        serializer = AssessmentTemplateSerializer(templates, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        if profile.role != 'admin':
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AssessmentTemplateSerializer(data=request.data)
        
        if serializer.is_valid():
            template = serializer.save(created_by=request.user)
            return Response(
                AssessmentTemplateDetailSerializer(template).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_detail(request, template_id):
    """Get template details with questions"""
    
    template = get_object_or_404(AssessmentTemplate, id=template_id)
    serializer = AssessmentTemplateDetailSerializer(template)
    return Response(serializer.data)



@swagger_auto_schema(methods=['POST'], request_body=AssessmentEvidenceSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def evidence_list_create(request, assessment_id):
    """List or upload evidence for assessment"""
    profile = request.user.profile
    
    assessment = get_object_or_404(VendorAssessment, id=assessment_id)
    
    if assessment.vendor.organization != profile.organization:
        return Response(
            {'error': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        evidence = AssessmentEvidence.objects.filter(assessment=assessment)
        serializer = AssessmentEvidenceSerializer(evidence, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = AssessmentEvidenceSerializer(data=request.data)
        
        if serializer.is_valid():
            evidence = serializer.save(
                assessment=assessment,
                uploaded_by=request.user
            )
            return Response(
                AssessmentEvidenceSerializer(evidence).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def evidence_delete(request, evidence_id):
    """Delete evidence"""
    profile = request.user.profile
    
    evidence = get_object_or_404(AssessmentEvidence, id=evidence_id)
    
    if evidence.assessment.vendor.organization != profile.organization:
        return Response(
            {'error': 'Not authorized'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Can only delete if uploader or admin
    if evidence.uploaded_by != request.user and profile.role != 'admin':
        return Response(
            {'error': 'Only the uploader or admin can delete evidence'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    evidence.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)