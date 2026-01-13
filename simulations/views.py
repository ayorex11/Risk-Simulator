from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from decimal import Decimal

from .models import (
    BusinessProcess, ScenarioTemplate, Simulation,
    SimulationResult, SimulationScenario, SimulationComparison
)
from vendors.models import Vendor
from .serializers import (
    BusinessProcessSerializer, BusinessProcessListSerializer,
    ScenarioTemplateSerializer, SimulationScenarioSerializer,
    SimulationListSerializer, SimulationDetailSerializer,
    SimulationCreateSerializer, SimulationResultSerializer,
    SimulationExecutionSerializer, WhatIfAnalysisSerializer,
    SimulationComparisonRequestSerializer, SimulationComparisonSerializer,
    SimulationSummarySerializer, MonteCarloResultSerializer,
    BatchSimulationSerializer
)
from drf_yasg.utils import swagger_auto_schema
import logging

logger = logging.getLogger('simulations')
# ==================== BUSINESS PROCESS ENDPOINTS ====================

@swagger_auto_schema(methods=['POST'], request_body=BusinessProcessSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def process_list_create(request):
    """List business processes or create new process"""
    
    if not hasattr(request.user, 'profile') or not request.user.profile.organization:
        return Response(
            {'error': 'Organization not found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.method == 'GET':
        processes = BusinessProcess.objects.filter(
            organization=request.user.profile.organization
        )
        
        # Apply filters
        criticality = request.query_params.get('criticality_level')
        if criticality:
            processes = processes.filter(criticality_level=criticality)
        
        # Search
        search = request.query_params.get('search')
        if search:
            processes = processes.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        processes = processes.order_by('-criticality_level', 'name')
        
        serializer = BusinessProcessListSerializer(processes, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        if request.user.profile.role not in ['admin', 'analyst', 'manager']:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BusinessProcessSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            process = serializer.save()
            return Response(
                BusinessProcessSerializer(process).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(methods=['PUT', 'PATCH'], request_body=BusinessProcessSerializer)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def process_detail(request, process_id):
    """Get, update, or delete a business process"""
    
    process = get_object_or_404(
        BusinessProcess,
        id=process_id,
        organization=request.user.profile.organization
    )
    
    if request.method == 'GET':
        serializer = BusinessProcessSerializer(process)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        if request.user.profile.role not in ['admin', 'analyst', 'manager']:
            return Response(
                {'error': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BusinessProcessSerializer(
            process,
            data=request.data,
            partial=request.method == 'PATCH',
            context={'request': request}
        )
        
        if serializer.is_valid():
            process = serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if request.user.profile.role != 'admin':
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        process.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== SCENARIO TEMPLATE ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scenario_template_list(request):
    """List all scenario templates"""
    
    templates = ScenarioTemplate.objects.filter(is_active=True)
    serializer = ScenarioTemplateSerializer(templates, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scenario_template_detail(request, template_id):
    """Get scenario template details"""
    
    template = get_object_or_404(ScenarioTemplate, id=template_id)
    serializer = ScenarioTemplateSerializer(template)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scenario_parameters(request, template_id):
    """Get parameter schema for scenario template"""
    
    template = get_object_or_404(ScenarioTemplate, id=template_id)
    
    # Add descriptions for parameters based on scenario type
    parameter_descriptions = {}
    
    if template.scenario_type == 'data_breach':
        parameter_descriptions = {
            'breach_vector': 'How the breach occurred (phishing, malware, etc.)',
            'records_compromised': 'Number of records affected',
            'data_types': 'Types of data exposed (PII, financial, healthcare)',
            'detection_time_hours': 'Time to detect the breach',
            'attacker_dwell_time_days': 'How long attacker had access'
        }
    elif template.scenario_type == 'ransomware':
        parameter_descriptions = {
            'encryption_scope': 'Extent of encryption (partial, full)',
            'ransom_amount': 'Demanded ransom in USD',
            'downtime_hours': 'Expected downtime duration',
            'backup_available': 'Whether backups are available',
            'restoration_difficulty': 'Difficulty of restoration (low, medium, high)'
        }

    elif template.scenario_type == 'service_disruption':
        parameter_descriptions = {
            'disruption_cause': 'Cause of disruption (DDoS, hardware failure, etc.)',
            'affected_services': 'Services impacted by the disruption',
            'duration_hours': 'Duration of the disruption',
            'customer_impact_level': 'Level of customer impact (low, medium, high)',
            'mitigation_measures': 'Measures in place to mitigate disruption'
        }

    elif template.scenario_type == 'supply_chain':
        parameter_descriptions = {
            'supplier_type': 'Type of supplier affected',
            'disruption_type': 'Type of disruption (delay, quality issue, etc.)',
            'duration_days': 'Duration of the disruption',
            'criticality_level': 'Criticality of the supplier to operations',
            'mitigation_strategies': 'Strategies to mitigate supply chain risks'
        }
    
    elif template.scenario_type == 'multi_vendor':
        parameter_descriptions = {
            'vendors_involved': 'List of vendors involved in the scenario',
            'disruption_cause': 'Cause of disruption affecting multiple vendors',
            'overall_duration_days': 'Overall duration of the disruption',
            'cascading_effects': 'Potential cascading effects on operations',
            'risk_mitigation_plans': 'Plans to mitigate risks from multiple vendors'
        }
    
    return Response({
        'scenario_type': template.scenario_type,
        'name': template.name,
        'description': template.description,
        'default_parameters': template.default_parameters,
        'calculation_config': template.calculation_config,
        'parameter_descriptions': parameter_descriptions
    })


# ==================== SIMULATION ENDPOINTS ====================

@swagger_auto_schema(methods=['POST'], request_body=SimulationCreateSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def simulation_list_create(request):
    """List simulations or create new simulation"""
    
    if not hasattr(request.user, 'profile') or not request.user.profile.organization:
        return Response(
            {'error': 'Organization not found'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.method == 'GET':
        simulations = Simulation.objects.filter(
            organization=request.user.profile.organization
        )
        
        # Apply filters
        sim_status = request.query_params.get('status')
        if sim_status:
            simulations = simulations.filter(status=sim_status)
        
        scenario_type = request.query_params.get('scenario_type')
        if scenario_type:
            simulations = simulations.filter(scenario_template__scenario_type=scenario_type)
        
        vendor_id = request.query_params.get('vendor_id')
        if vendor_id:
            simulations = simulations.filter(target_vendor_id=vendor_id)
        
        # Ordering
        simulations = simulations.order_by('-created_at')
        
        serializer = SimulationListSerializer(simulations, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        if not request.user.profile.can_create_simulations:
            return Response(
                {'error': 'Insufficient permissions to create simulations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SimulationCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Verify vendor belongs to organization
            vendor = serializer.validated_data['target_vendor']
            if vendor.organization != request.user.profile.organization:
                return Response(
                    {'error': 'Vendor does not belong to your organization'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            simulation = serializer.save()
            return Response(
                SimulationDetailSerializer(simulation).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def simulation_detail(request, simulation_id):
    """Get or delete a simulation"""
    
    simulation = get_object_or_404(
        Simulation,
        id=simulation_id,
        organization=request.user.profile.organization
    )
    
    if request.method == 'GET':
        serializer = SimulationDetailSerializer(simulation)
        return Response(serializer.data)
    
    elif request.method == 'DELETE':
        if request.user.profile.role != 'admin':
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        simulation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_simulation(request, simulation_id):
    """Execute a simulation - THE MAGIC HAPPENS HERE! ✨"""
    
    simulation = get_object_or_404(
        Simulation,
        id=simulation_id,
        organization=request.user.profile.organization
    )
    
    # Check if already completed
    force_rerun = request.data.get('force_rerun', False)
    
    if simulation.status == 'completed' and not force_rerun:
        return Response(
            {'error': 'Simulation already completed. Use force_rerun=true to re-execute.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if simulation.status == 'running':
        return Response(
            {'error': 'Simulation is currently running'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Import and execute simulation engine
        from .engine import SimulationEngine
        
        engine = SimulationEngine(simulation)
        result = engine.execute()
        
        # Generate executive summary
        from .utils import ReportGenerator
        executive_summary = ReportGenerator.generate_executive_summary(result)
        
        return Response({
            'message': 'Simulation completed successfully!',
            'simulation': SimulationDetailSerializer(simulation).data,
            'result': SimulationResultSerializer(result).data,
            'executive_summary': executive_summary,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Simulation execution failed: {str(e)}", exc_info=True)
        return Response({
            'error': 'Simulation execution failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(methods=['POST'], request_body=WhatIfAnalysisSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def what_if_analysis(request):
    """Run what-if analysis with parameter variations"""
    
    serializer = WhatIfAnalysisSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    base_simulation_id = serializer.validated_data['base_simulation_id']
    parameter_changes = serializer.validated_data['parameter_changes']
    scenario_name = serializer.validated_data['scenario_name']
    description = serializer.validated_data.get('description', '')
    
    # Get base simulation
    base_simulation = get_object_or_404(
        Simulation,
        id=base_simulation_id,
        organization=request.user.profile.organization
    )
    
    # Create new simulation with modified parameters
    new_params = base_simulation.parameters.copy()
    new_params.update(parameter_changes)
    
    new_simulation = Simulation.objects.create(
        organization=request.user.profile.organization,
        created_by=request.user,
        name=scenario_name,
        description=description or f"What-if analysis based on {base_simulation.name}",
        scenario_template=base_simulation.scenario_template,
        target_vendor=base_simulation.target_vendor,
        parameters=new_params,
        use_monte_carlo=base_simulation.use_monte_carlo,
        monte_carlo_iterations=base_simulation.monte_carlo_iterations,
        tags=['what-if-analysis', f'base:{str(base_simulation.id)}']
    )
    
    return Response({
        'message': 'What-if scenario created successfully',
        'base_simulation': SimulationListSerializer(base_simulation).data,
        'new_simulation': SimulationDetailSerializer(new_simulation).data,
        'parameter_changes': parameter_changes,
        'note': 'Execute the new simulation to see results'
    }, status=status.HTTP_201_CREATED)


@swagger_auto_schema(methods=['POST'], request_body=SimulationComparisonRequestSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def compare_simulations(request):
    """Compare multiple simulations"""
    
    serializer = SimulationComparisonRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    simulation_ids = serializer.validated_data['simulation_ids']
    
    simulations = Simulation.objects.filter(
        id__in=simulation_ids,
        organization=request.user.profile.organization
    )
    
    if simulations.count() != len(simulation_ids):
        return Response(
            {'error': 'One or more simulations not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Build comparison data
    comparison_data = []
    
    for sim in simulations:
        data = {
            'simulation_id': str(sim.id),
            'name': sim.name,
            'vendor': sim.target_vendor.name,
            'scenario_type': sim.scenario_template.scenario_type,
            'status': sim.status,
            'created_at': sim.created_at
        }
        
        # Add results if available
        if hasattr(sim, 'result'):
            result = sim.result
            data.update({
                'total_financial_impact': float(result.total_financial_impact),
                'direct_costs': float(result.direct_costs),
                'operational_costs': float(result.operational_costs),
                'regulatory_costs': float(result.regulatory_costs),
                'reputational_costs': float(result.reputational_costs),
                'downtime_hours': result.downtime_hours,
                'recovery_time_hours': result.estimated_recovery_time_hours,
                'risk_score': result.risk_score,
            })
        else:
            data['note'] = 'No results available - simulation not executed'
        
        comparison_data.append(data)
    
    # Calculate summary statistics
    completed_sims = [d for d in comparison_data if 'total_financial_impact' in d]
    
    summary_statistics = {}
    if completed_sims:
        impacts = [d['total_financial_impact'] for d in completed_sims]
        summary_statistics = {
            'total_simulations': len(comparison_data),
            'completed_simulations': len(completed_sims),
            'average_impact': sum(impacts) / len(impacts) if impacts else 0,
            'max_impact': max(impacts) if impacts else 0,
            'min_impact': min(impacts) if impacts else 0,
        }
    
    return Response({
        'simulations': SimulationListSerializer(simulations, many=True).data,
        'comparison_data': comparison_data,
        'summary_statistics': summary_statistics,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def simulation_summary(request):
    """Get simulation portfolio summary"""
    
    org = request.user.profile.organization
    simulations = Simulation.objects.filter(organization=org)
    
    # Recent simulations
    recent = simulations.order_by('-created_at')[:10]
    
    # Highest impact scenarios
    results = SimulationResult.objects.filter(
        simulation__organization=org
    ).order_by('-total_financial_impact')[:10]
    
    highest_impact = []
    for result in results:
        highest_impact.append(result.simulation)
    
    # By scenario type
    from django.db.models import Count
    by_scenario_type = {}
    scenario_counts = simulations.values('scenario_template__scenario_type').annotate(
        count=Count('id')
    )
    for item in scenario_counts:
        by_scenario_type[item['scenario_template__scenario_type']] = item['count']
    
    # By vendor
    by_vendor = {}
    vendor_counts = simulations.values('target_vendor__name').annotate(
        count=Count('id')
    )[:10]
    for item in vendor_counts:
        by_vendor[item['target_vendor__name']] = item['count']
    
    # Total estimated impact
    total_impact = SimulationResult.objects.filter(
        simulation__organization=org
    ).aggregate(Sum('total_financial_impact'))['total_financial_impact__sum'] or Decimal('0')
    
    # Average recovery time
    avg_recovery = SimulationResult.objects.filter(
        simulation__organization=org
    ).aggregate(Avg('estimated_recovery_time_hours'))['estimated_recovery_time_hours__avg'] or 0
    
    summary = {
        'total_simulations': simulations.count(),
        'completed_simulations': simulations.filter(status='completed').count(),
        'pending_simulations': simulations.filter(status='pending').count(),
        'failed_simulations': simulations.filter(status='failed').count(),
        'total_estimated_impact': float(total_impact),
        'average_recovery_time': avg_recovery,
        'by_scenario_type': by_scenario_type,
        'by_vendor': by_vendor,
        'recent_simulations': SimulationListSerializer(recent, many=True).data,
        'highest_impact_scenarios': SimulationListSerializer(highest_impact, many=True).data,
    }
    
    serializer = SimulationSummarySerializer(summary)
    return Response(serializer.data)


# ==================== SIMULATION RESULT ENDPOINTS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def result_detail(request, simulation_id):
    """Get simulation result"""
    
    simulation = get_object_or_404(
        Simulation,
        id=simulation_id,
        organization=request.user.profile.organization
    )
    
    if not hasattr(simulation, 'result'):
        return Response(
            {'error': 'No results available for this simulation'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = SimulationResultSerializer(simulation.result)
    return Response(serializer.data)


# ==================== BATCH OPERATIONS ====================

@swagger_auto_schema(methods=['POST'], request_body=BatchSimulationSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_create_simulations(request):
    """Create multiple simulations at once"""
    
    if not request.user.profile.can_create_simulations:
        return Response(
            {'error': 'Insufficient permissions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = BatchSimulationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    vendor_ids = serializer.validated_data['vendor_ids']
    scenario_template_id = serializer.validated_data['scenario_template_id']
    base_parameters = serializer.validated_data['base_parameters']
    use_monte_carlo = serializer.validated_data['use_monte_carlo']
    monte_carlo_iterations = serializer.validated_data['monte_carlo_iterations']
    
    # Verify vendors and template
    vendors = Vendor.objects.filter(
        id__in=vendor_ids,
        organization=request.user.profile.organization
    )
    
    if vendors.count() != len(vendor_ids):
        return Response(
            {'error': 'One or more vendors not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    template = get_object_or_404(ScenarioTemplate, id=scenario_template_id)
    
    # Create simulations
    created_simulations = []
    
    for vendor in vendors:
        simulation = Simulation.objects.create(
            organization=request.user.profile.organization,
            created_by=request.user,
            name=f"{template.name} - {vendor.name}",
            description=f"Batch simulation for {vendor.name}",
            scenario_template=template,
            target_vendor=vendor,
            parameters=base_parameters,
            use_monte_carlo=use_monte_carlo,
            monte_carlo_iterations=monte_carlo_iterations,
            tags=['batch-created']
        )
        created_simulations.append(simulation)
    
    return Response({
        'message': f'Successfully created {len(created_simulations)} simulations',
        'simulations': SimulationListSerializer(created_simulations, many=True).data
    }, status=status.HTTP_201_CREATED)