import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import Simulation, SimulationResult, BusinessProcess
from vendors.models import Vendor

logger = logging.getLogger('simulations')


class SimulationEngine:
    """
    Main simulation engine that orchestrates risk scenario execution
    """
    
    def __init__(self, simulation: Simulation):
        self.simulation = simulation
        self.vendor = simulation.target_vendor
        self.organization = simulation.organization
        self.scenario_type = simulation.scenario_template.scenario_type
        self.parameters = simulation.parameters
        self.config = settings.SIMULATION_CONFIG
        
        # Results storage
        self.results = {
            'direct_costs': Decimal('0'),
            'operational_costs': Decimal('0'),
            'regulatory_costs': Decimal('0'),
            'reputational_costs': Decimal('0'),
            'downtime_hours': 0.0,
            'productivity_loss_percentage': 0.0,
            'customers_affected': 0,
            'estimated_recovery_time_hours': 0.0,
            'recovery_complexity': 'medium',
            'cascading_vendor_impacts': [],
            'total_cascading_impact': Decimal('0'),
            'affected_process_ids': [],
            'impact_breakdown': {},
            'risk_score': 0.0
        }
    
    def execute(self) -> SimulationResult:
        """
        Main execution method - The magic starts here! ✨
        """
        logger.info(f"🎬 Starting simulation: {self.simulation.name}")
        
        try:
            # Update simulation status
            self.simulation.status = 'running'
            self.simulation.started_at = timezone.now()
            self.simulation.save()
            
            start_time = datetime.now()
            
            # Execute simulation based on scenario type
            if self.scenario_type == 'data_breach':
                self._simulate_data_breach()
            elif self.scenario_type == 'ransomware':
                self._simulate_ransomware()
            elif self.scenario_type == 'service_disruption':
                self._simulate_service_disruption()
            elif self.scenario_type == 'supply_chain':
                self._simulate_supply_chain_compromise()
            elif self.scenario_type == 'multi_vendor':
                self._simulate_multi_vendor_failure()
            else:
                raise ValueError(f"Unknown scenario type: {self.scenario_type}")
            
            # Calculate cascading impacts
            self._calculate_cascading_impacts()
            
            # Calculate overall risk score
            self._calculate_risk_score()
            
            # Run Monte Carlo if enabled
            if self.simulation.use_monte_carlo:
                self._run_monte_carlo_simulation()
            
            # Save results
            result = self._save_results()
            
            # Update simulation status
            execution_time = (datetime.now() - start_time).total_seconds()
            self.simulation.status = 'completed'
            self.simulation.completed_at = timezone.now()
            self.simulation.execution_time = execution_time
            self.simulation.save()
            
            logger.info(f"✅ Simulation completed in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Simulation failed: {str(e)}", exc_info=True)
            self.simulation.status = 'failed'
            self.simulation.error_message = str(e)
            self.simulation.save()
            raise
    
    def _simulate_data_breach(self):
        """
        Simulate data breach scenario
        💾 Unauthorized access and data exfiltration
        """
        logger.info("💾 Simulating data breach scenario")
        
        # Get parameters
        records_compromised = self.parameters.get('records_compromised', 10000)
        data_types = self.parameters.get('data_types', ['PII'])
        detection_time_hours = self.parameters.get('detection_time_hours', 72)
        breach_vector = self.parameters.get('breach_vector', 'phishing')
        
        # Calculate direct costs
        # Forensics, legal, notification
        base_incident_cost = Decimal('50000')  # Base investigation cost
        per_record_cost = Decimal(str(self.config['PER_RECORD_BREACH_COST']))
        
        self.results['direct_costs'] = (
            base_incident_cost + 
            (Decimal(str(records_compromised)) * per_record_cost)
        )
        
        # Calculate regulatory costs based on data types
        regulatory_cost = Decimal('0')
        
        if 'PII' in data_types or 'financial' in data_types:
            # GDPR penalties
            gdpr_per_record = Decimal(str(self.config['GDPR_PENALTY_PER_RECORD']))
            regulatory_cost += Decimal(str(records_compromised)) * gdpr_per_record
        
        if 'healthcare' in data_types:
            # HIPAA penalties
            hipaa_per_record = Decimal(str(self.config['HIPAA_PENALTY_PER_RECORD']))
            regulatory_cost += Decimal(str(records_compromised)) * hipaa_per_record
        
        self.results['regulatory_costs'] = regulatory_cost
        
        # Calculate reputational costs (customer churn)
        industry = self.vendor.industry.lower()
        churn_rate = self.config['CHURN_RATES'].get(industry, 0.15)
        
        # Estimate customers affected (10% of records = unique customers)
        customers_affected = int(records_compromised * 0.1)
        customers_lost = int(customers_affected * churn_rate)
        
        # Average customer lifetime value (industry dependent)
        avg_customer_value = Decimal('500')  # Could be parameterized
        
        self.results['reputational_costs'] = (
            Decimal(str(customers_lost)) * avg_customer_value
        )
        self.results['customers_affected'] = customers_affected
        
        # Operational costs (response time and recovery)
        response_hours = detection_time_hours + 48  # Detection + initial response
        hourly_cost = Decimal('250')  # IT team hourly rate
        
        self.results['operational_costs'] = (
            Decimal(str(response_hours)) * hourly_cost
        )
        
        # Downtime and recovery
        self.results['downtime_hours'] = float(response_hours * 0.3)  # 30% downtime
        self.results['estimated_recovery_time_hours'] = float(
            response_hours * self.config['RECOVERY_TIME_MULTIPLIERS']['data_breach']
        )
        self.results['recovery_complexity'] = 'high' if records_compromised > 50000 else 'medium'
        
        # Affected processes (processes that use this vendor)
        affected_processes = BusinessProcess.objects.filter(
            organization=self.organization,
            dependent_vendors=self.vendor
        )
        self.results['affected_process_ids'] = [p.id for p in affected_processes]
        
        # Impact breakdown
        self.results['impact_breakdown'] = {
            'breach_details': {
                'records_compromised': records_compromised,
                'data_types': data_types,
                'detection_time_hours': detection_time_hours,
                'breach_vector': breach_vector,
            },
            'cost_breakdown': {
                'investigation': float(base_incident_cost),
                'per_record_cost': float(per_record_cost),
                'notification_costs': float(per_record_cost * Decimal(str(records_compromised)) * Decimal('0.3')),
                'legal_costs': float(base_incident_cost * Decimal('0.5')),
            },
            'customer_impact': {
                'customers_affected': customers_affected,
                'estimated_churn': customers_lost,
                'churn_rate': churn_rate,
            }
        }
        
        logger.info(f"💾 Data breach impact: {records_compromised} records, ${self.results['direct_costs'] + self.results['regulatory_costs']}")
    
    def _simulate_ransomware(self):
        """
        Simulate ransomware attack scenario
        🔒 Encryption with ransom demands
        """
        logger.info("🔒 Simulating ransomware attack")
        
        # Get parameters
        ransom_amount = Decimal(str(self.parameters.get('ransom_amount', 500000)))
        downtime_hours = self.parameters.get('downtime_hours', 168)  # 1 week
        encryption_scope = self.parameters.get('encryption_scope', 'full')
        backup_available = self.parameters.get('backup_available', True)
        
        # Direct costs
        if not backup_available:
            # May need to pay ransom or lose data
            ransom_payment_probability = 0.3
            self.results['direct_costs'] = ransom_amount * Decimal(str(ransom_payment_probability))
        else:
            # Restoration costs
            self.results['direct_costs'] = Decimal('100000')  # Restoration and cleanup
        
        # Operational costs - MASSIVE impact
        affected_processes = BusinessProcess.objects.filter(
            organization=self.organization,
            dependent_vendors=self.vendor
        )
        
        total_hourly_cost = sum(
            float(p.hourly_operating_cost) 
            for p in affected_processes
        )
        
        scope_multiplier = 1.0 if encryption_scope == 'full' else 0.5
        
        self.results['operational_costs'] = (
            Decimal(str(total_hourly_cost)) * 
            Decimal(str(downtime_hours)) * 
            Decimal(str(scope_multiplier))
        )
        
        # Downtime
        self.results['downtime_hours'] = float(downtime_hours)
        self.results['productivity_loss_percentage'] = 80.0 if encryption_scope == 'full' else 40.0
        
        # Recovery time
        base_recovery = downtime_hours
        if backup_available:
            recovery_multiplier = 0.5  # Faster with backups
        else:
            recovery_multiplier = 2.0  # Much slower without backups
        
        self.results['estimated_recovery_time_hours'] = float(
            base_recovery * recovery_multiplier * 
            self.config['RECOVERY_TIME_MULTIPLIERS']['ransomware']
        )
        
        self.results['recovery_complexity'] = 'very_high' if not backup_available else 'high'
        
        # Affected processes
        self.results['affected_process_ids'] = [p.id for p in affected_processes]
        
        # Regulatory costs (if data potentially compromised)
        if not backup_available:
            self.results['regulatory_costs'] = Decimal('250000')  # Potential data loss notifications
        
        # Reputational costs
        # Ransomware attacks damage reputation significantly
        self.results['reputational_costs'] = Decimal('500000')
        
        # Impact breakdown
        self.results['impact_breakdown'] = {
            'ransomware_details': {
                'ransom_demanded': float(ransom_amount),
                'downtime_hours': downtime_hours,
                'encryption_scope': encryption_scope,
                'backup_available': backup_available,
            },
            'recovery_strategy': 'backup_restoration' if backup_available else 'potential_ransom_payment',
            'affected_systems': encryption_scope,
        }
        
        logger.info(f"🔒 Ransomware impact: {downtime_hours}h downtime, ${self.results['operational_costs']}")
    
    def _simulate_service_disruption(self):
        """
        Simulate service outage scenario
        ⚠️ Service unavailability
        """
        logger.info("⚠️ Simulating service disruption")
        
        # Get parameters
        duration_hours = self.parameters.get('duration_hours', 24)
        disruption_cause = self.parameters.get('disruption_cause', 'infrastructure_failure')
        customer_impact_percentage = self.parameters.get('customer_impact_percentage', 50)
        
        # Operational costs based on affected processes
        affected_processes = BusinessProcess.objects.filter(
            organization=self.organization,
            dependent_vendors=self.vendor
        )
        
        # Calculate based on criticality
        total_impact = Decimal('0')
        for process in affected_processes:
            # Higher criticality = higher impact
            criticality_multiplier = Decimal(str(process.criticality_level / 5.0))
            process_impact = (
                process.hourly_operating_cost * 
                Decimal(str(duration_hours)) * 
                criticality_multiplier
            )
            total_impact += process_impact
        
        self.results['operational_costs'] = total_impact
        
        # Direct costs (investigation and remediation)
        base_cost = Decimal('25000')
        complexity_multiplier = 1.5 if disruption_cause == 'cyber_attack' else 1.0
        self.results['direct_costs'] = base_cost * Decimal(str(complexity_multiplier))
        
        # Downtime
        self.results['downtime_hours'] = float(duration_hours)
        self.results['productivity_loss_percentage'] = float(customer_impact_percentage)
        
        # Recovery time
        self.results['estimated_recovery_time_hours'] = float(
            duration_hours * self.config['RECOVERY_TIME_MULTIPLIERS']['service_disruption']
        )
        self.results['recovery_complexity'] = 'medium'
        
        # SLA penalties (if applicable)
        sla_penalty = Decimal(str(self.vendor.contract_value)) * Decimal('0.05')  # 5% penalty
        self.results['regulatory_costs'] = sla_penalty
        
        # Customer impact
        if customer_impact_percentage > 70:
            self.results['reputational_costs'] = Decimal('200000')
        elif customer_impact_percentage > 40:
            self.results['reputational_costs'] = Decimal('100000')
        else:
            self.results['reputational_costs'] = Decimal('50000')
        
        # Affected processes
        self.results['affected_process_ids'] = [p.id for p in affected_processes]
        
        # Impact breakdown
        self.results['impact_breakdown'] = {
            'disruption_details': {
                'duration_hours': duration_hours,
                'cause': disruption_cause,
                'customer_impact_percentage': customer_impact_percentage,
            },
            'sla_penalty': float(sla_penalty),
            'affected_process_count': affected_processes.count(),
        }
        
        logger.info(f"⚠️ Service disruption: {duration_hours}h, ${total_impact}")
    
    def _simulate_supply_chain_compromise(self):
        """
        Simulate supply chain attack scenario
        🔗 Malicious code in vendor software (SolarWinds-style)
        """
        logger.info("🔗 Simulating supply chain compromise")
        
        # Get parameters
        affected_downstream = self.parameters.get('affected_downstream_count', 100)
        detection_delay_days = self.parameters.get('detection_delay_days', 180)
        compromise_method = self.parameters.get('compromise_method', 'build_system')
        
        # This is SEVERE - affects the vendor and all their customers
        
        # Direct costs - massive investigation
        base_cost = Decimal('1000000')  # Million dollar investigation
        self.results['direct_costs'] = base_cost
        
        # Impact on YOUR organization as a customer
        # Code review, system rebuilds, incident response
        self.results['operational_costs'] = Decimal('500000')
        
        # Regulatory costs - notification requirements
        # Even though you're the victim, you may have obligations
        self.results['regulatory_costs'] = Decimal('300000')
        
        # Reputational costs - HUGE
        # Your organization used compromised vendor
        self.results['reputational_costs'] = Decimal('2000000')
        
        # Long detection time = long exposure
        exposure_hours = detection_delay_days * 24
        self.results['downtime_hours'] = exposure_hours * 0.1  # 10% of exposure time
        
        # Recovery is COMPLEX and LONG
        self.results['estimated_recovery_time_hours'] = float(
            720 * self.config['RECOVERY_TIME_MULTIPLIERS']['supply_chain']  # 30 days base
        )
        self.results['recovery_complexity'] = 'very_high'
        
        # ALL processes potentially affected
        affected_processes = BusinessProcess.objects.filter(
            organization=self.organization,
            dependent_vendors=self.vendor
        )
        self.results['affected_process_ids'] = [p.id for p in affected_processes]
        
        # Impact breakdown
        self.results['impact_breakdown'] = {
            'supply_chain_details': {
                'compromise_method': compromise_method,
                'detection_delay_days': detection_delay_days,
                'downstream_affected': affected_downstream,
                'exposure_duration_hours': exposure_hours,
            },
            'remediation_required': [
                'Full code audit',
                'System rebuilds',
                'Certificate rotation',
                'Enhanced monitoring',
                'Third-party security audit'
            ],
            'severity': 'CRITICAL',
        }
        
        logger.info(f"🔗 Supply chain compromise: {detection_delay_days} days undetected, ${base_cost + Decimal('500000')}")
    
    def _simulate_multi_vendor_failure(self):
        """
        Simulate cascading multi-vendor failure
        ⛓️ Domino effect across dependent vendors
        """
        logger.info("⛓️ Simulating multi-vendor failure")
        
        # Get parameters
        initial_failure_type = self.parameters.get('initial_failure_type', 'data_breach')
        cascade_probability = self.parameters.get('cascade_probability', 0.6)
        
        # Start with initial vendor failure
        # Simulate the initial failure type
        if initial_failure_type == 'data_breach':
            self._simulate_data_breach()
        elif initial_failure_type == 'ransomware':
            self._simulate_ransomware()
        else:
            self._simulate_service_disruption()
        
        # Store initial impact
        initial_impact = (
            self.results['direct_costs'] + 
            self.results['operational_costs'] + 
            self.results['regulatory_costs'] + 
            self.results['reputational_costs']
        )
        
        # Now calculate cascading impacts
        cascade_impacts = []
        
        # Get dependent vendors
        dependent_vendors = self.vendor.dependent_vendors.all()
        
        for dep_vendor in dependent_vendors:
            # Probability this vendor is also affected
            import random
            if random.random() < cascade_probability:
                # This vendor is affected - calculate impact
                vendor_impact = self._calculate_vendor_cascade_impact(dep_vendor)
                cascade_impacts.append({
                    'vendor_id': str(dep_vendor.id),
                    'vendor_name': dep_vendor.name,
                    'impact': float(vendor_impact),
                    'reason': 'dependency_failure'
                })
        
        # Vendors that depend on THIS vendor
        depending_vendors = self.vendor.dependency_of.all()
        
        for dep_vendor in depending_vendors:
            if random.random() < cascade_probability * 0.8:  # Slightly lower probability
                vendor_impact = self._calculate_vendor_cascade_impact(dep_vendor)
                cascade_impacts.append({
                    'vendor_id': str(dep_vendor.id),
                    'vendor_name': dep_vendor.name,
                    'impact': float(vendor_impact),
                    'reason': 'upstream_failure'
                })
        
        # Calculate total cascading impact
        total_cascade = sum(Decimal(str(c['impact'])) for c in cascade_impacts)
        
        self.results['cascading_vendor_impacts'] = cascade_impacts
        self.results['total_cascading_impact'] = total_cascade
        
        # Multiply all costs by cascade factor
        cascade_multiplier = Decimal('1.5')
        self.results['direct_costs'] *= cascade_multiplier
        self.results['operational_costs'] *= cascade_multiplier
        self.results['recovery_complexity'] = 'very_high'
        
        # Impact breakdown
        self.results['impact_breakdown']['cascade_analysis'] = {
            'initial_failure': initial_failure_type,
            'initial_impact': float(initial_impact),
            'cascade_probability': cascade_probability,
            'vendors_affected': len(cascade_impacts),
            'total_cascade_impact': float(total_cascade),
            'cascade_multiplier': float(cascade_multiplier),
        }
        
        logger.info(f"⛓️ Multi-vendor failure: {len(cascade_impacts)} vendors affected, total: ${initial_impact + total_cascade}")
    
    def _calculate_vendor_cascade_impact(self, vendor: Vendor) -> Decimal:
        """Calculate impact of cascade on a dependent vendor"""
        # Base impact on vendor's contract value and criticality
        base_impact = vendor.contract_value * Decimal('0.2')  # 20% of contract value
        
        # Adjust by vendor risk level
        risk_multipliers = {
            'low': Decimal('0.5'),
            'medium': Decimal('1.0'),
            'high': Decimal('1.5'),
            'critical': Decimal('2.0'),
        }
        
        multiplier = risk_multipliers.get(vendor.risk_level, Decimal('1.0'))
        
        return base_impact * multiplier
    
    def _calculate_cascading_impacts(self):
        """
        Calculate cascading impacts across vendor dependencies
        This is called for all scenarios except multi_vendor (which handles it specially)
        """
        if self.scenario_type == 'multi_vendor':
            return  # Already handled in multi_vendor simulation
        
        logger.info("🌊 Calculating cascading impacts")
        
        cascade_impacts = []
        
        # Check vendor dependencies
        dependent_vendors = self.vendor.dependent_vendors.all()
        
        for dep_vendor in dependent_vendors:
            # Impact based on dependency strength
            impact = self._calculate_vendor_cascade_impact(dep_vendor)
            
            cascade_impacts.append({
                'vendor_id': str(dep_vendor.id),
                'vendor_name': dep_vendor.name,
                'impact': float(impact),
                'reason': 'direct_dependency'
            })
        
        # Calculate total
        total_cascade = sum(Decimal(str(c['impact'])) for c in cascade_impacts)
        
        self.results['cascading_vendor_impacts'] = cascade_impacts
        self.results['total_cascading_impact'] = total_cascade
        
        if cascade_impacts:
            logger.info(f"🌊 Cascading impact: {len(cascade_impacts)} vendors, ${total_cascade}")
    
    def _calculate_risk_score(self):
        """
        Calculate overall risk score for this simulation (0-100)
        """
        # Normalize financial impact to 0-100 scale
        total_financial = (
            self.results['direct_costs'] + 
            self.results['operational_costs'] + 
            self.results['regulatory_costs'] + 
            self.results['reputational_costs'] +
            self.results['total_cascading_impact']
        )
        
        # Use logarithmic scale for financial impact
        # $100K = 50, $1M = 75, $10M = 90, $100M = 100
        import math
        if total_financial > 0:
            financial_score = min(100, 30 + (20 * math.log10(float(total_financial) / 100000)))
        else:
            financial_score = 0
        
        # Downtime score (0-25)
        downtime_score = min(25, self.results['downtime_hours'] / 10)
        
        # Recovery complexity score (0-20)
        complexity_scores = {
            'low': 5,
            'medium': 10,
            'high': 15,
            'very_high': 20,
        }
        complexity_score = complexity_scores.get(self.results['recovery_complexity'], 10)
        
        # Vendor base risk (0-25)
        vendor_risk_score = self.vendor.overall_risk_score / 4
        
        # Combine scores
        self.results['risk_score'] = min(100, 
            financial_score + downtime_score + complexity_score + vendor_risk_score
        )
        
        logger.info(f"📊 Risk score calculated: {self.results['risk_score']:.2f}/100")
    
    def _run_monte_carlo_simulation(self):
        """
        Run Monte Carlo simulation for probabilistic analysis
        🎲 Statistical magic!
        """
        logger.info(f"🎲 Running Monte Carlo simulation ({self.simulation.monte_carlo_iterations} iterations)")
        
        import numpy as np
        
        iterations = self.simulation.monte_carlo_iterations
        results_distribution = []
        
        # Store current results as baseline
        baseline_total = (
            self.results['direct_costs'] + 
            self.results['operational_costs'] + 
            self.results['regulatory_costs'] + 
            self.results['reputational_costs']
        )
        
        # Run iterations with varying parameters
        for i in range(iterations):
            # Vary costs by ±30% using normal distribution
            variation = np.random.normal(1.0, 0.15)  # Mean 1.0, std 0.15
            variation = max(0.7, min(1.3, variation))  # Clip to ±30%
            
            iteration_total = float(baseline_total) * variation
            results_distribution.append(iteration_total)
        
        # Calculate statistics
        results_array = np.array(results_distribution)
        
        monte_carlo_results = {
            'iterations': iterations,
            'mean': float(np.mean(results_array)),
            'median': float(np.median(results_array)),
            'std_dev': float(np.std(results_array)),
            'min': float(np.min(results_array)),
            'max': float(np.max(results_array)),
            'percentile_50': float(np.percentile(results_array, 50)),
            'percentile_75': float(np.percentile(results_array, 75)),
            'percentile_90': float(np.percentile(results_array, 90)),
            'percentile_95': float(np.percentile(results_array, 95)),
            'percentile_99': float(np.percentile(results_array, 99)),
            'confidence_intervals': {
                '90': {
                    'lower': float(np.percentile(results_array, 5)),
                    'upper': float(np.percentile(results_array, 95)),
                },
                '95': {
                    'lower': float(np.percentile(results_array, 2.5)),
                    'upper': float(np.percentile(results_array, 97.5)),
                }
            },
            'distribution': results_distribution[:100]  # Store first 100 for visualization
        }
        
        self.results['monte_carlo_results'] = monte_carlo_results
        
        logger.info(f"🎲 Monte Carlo: Mean=${monte_carlo_results['mean']:,.0f}, "
                   f"95th percentile=${monte_carlo_results['percentile_95']:,.0f}")
    
    @transaction.atomic
    def _save_results(self) -> SimulationResult:
        """
        Save simulation results to database
        """
        logger.info("💾 Saving simulation results")
        
        # Calculate total financial impact
        total_impact = (
            self.results['direct_costs'] + 
            self.results['operational_costs'] + 
            self.results['regulatory_costs'] + 
            self.results['reputational_costs'] +
            self.results['total_cascading_impact']
        )
        
        # Create or update result
        result, created = SimulationResult.objects.update_or_create(
            simulation=self.simulation,
            defaults={
                'direct_costs': self.results['direct_costs'],
                'operational_costs': self.results['operational_costs'],
                'regulatory_costs': self.results['regulatory_costs'],
                'reputational_costs': self.results['reputational_costs'],
                'total_financial_impact': total_impact,
                'downtime_hours': self.results['downtime_hours'],
                'productivity_loss_percentage': self.results['productivity_loss_percentage'],
                'customers_affected': self.results['customers_affected'],
                'estimated_recovery_time_hours': self.results['estimated_recovery_time_hours'],
                'recovery_complexity': self.results['recovery_complexity'],
                'cascading_vendor_impacts': self.results['cascading_vendor_impacts'],
                'total_cascading_impact': self.results['total_cascading_impact'],
                'impact_breakdown': self.results['impact_breakdown'],
                'risk_score': self.results['risk_score'],
                'monte_carlo_results': self.results.get('monte_carlo_results', {}),
            }
        )
        
        # Link affected processes
        if self.results['affected_process_ids']:
            result.affected_processes.set(self.results['affected_process_ids'])
        
        logger.info(f"💾 Results saved: Total impact ${total_impact:,.2f}")
        
        return result