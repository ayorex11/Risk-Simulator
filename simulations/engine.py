import logging
import random as _random
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import Simulation, SimulationResult, BusinessProcess
from vendors.models import Vendor
from .utils import CascadeAnalyzer, RiskScoreCalculator, ReportGenerator
import copy
import numpy as np
import scipy.stats as stats

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
        self.results = self._empty_results()

    def _empty_results(self) -> dict:
        """Return a clean results dictionary. Call this instead of inlining the dict."""
        return {
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
            'risk_score': 0.0,
            # Monte Carlo results are stored here only when actually run
        }

    def execute(self) -> SimulationResult:
        """
        Main execution method
        """
        logger.info("Starting simulation: %s", self.simulation.name)

        try:
            # Update simulation status
            self.simulation.status = 'running'
            self.simulation.started_at = timezone.now()
            self.simulation.save()

            start_time = datetime.now()

            # Execute simulation based on scenario type
            self._dispatch_scenario(self.scenario_type)

            # Calculate cascading impacts (skipped for multi_vendor — already done inside)
            self._calculate_cascading_impacts()

            # Fallback: ensure customers_affected has a meaningful value.
            # Each scenario sets this itself where possible. This fallback only
            # fires if a scenario could not determine it. We use a conservative
            # 10% default rather than reading customer_impact_percentage, which
            # is only a parameter for service_disruption — not all scenario types.
            if self.results['customers_affected'] == 0:
                org_customer_base = getattr(self.organization, 'customer_base', None) or 10000
                customer_impact_pct = self.parameters.get('customer_impact_percentage', 10) / 100
                self.results['customers_affected'] = int(org_customer_base * customer_impact_pct)

            # Calculate overall risk score
            self._calculate_risk_score()

            # Run Monte Carlo if enabled — results stored in self.results['monte_carlo_results']
            if self.simulation.use_monte_carlo:
                self._run_monte_carlo_simulation()

            # Save results to DB
            result = self._save_results()

            # Update simulation status
            execution_time = (datetime.now() - start_time).total_seconds()
            self.simulation.status = 'completed'
            self.simulation.completed_at = timezone.now()
            self.simulation.execution_time = execution_time
            self.simulation.save()

            logger.info("Simulation completed in %.2fs", execution_time)
            return result

        except Exception as e:
            logger.error("Simulation failed: %s", str(e), exc_info=True)
            self.simulation.status = 'failed'
            self.simulation.error_message = str(e)
            self.simulation.save()
            raise

    def _dispatch_scenario(self, scenario_type: str):
        """Route to the correct scenario method."""
        dispatch = {
            'data_breach': self._simulate_data_breach,
            'ransomware': self._simulate_ransomware,
            'service_disruption': self._simulate_service_disruption,
            'supply_chain': self._simulate_supply_chain_compromise,
            'multi_vendor': self._simulate_multi_vendor_failure,
        }
        handler = dispatch.get(scenario_type)
        if handler is None:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        handler()

    # ------------------------------------------------------------------
    # Scenario simulations
    # ------------------------------------------------------------------

    def _simulate_data_breach(self):
        """
        Simulate data breach scenario — unauthorised access and data exfiltration.
        """
        logger.info("Simulating data breach scenario")

        records_compromised = self.parameters.get('records_compromised', 10000)
        data_types = self.parameters.get('data_types', ['PII'])
        detection_time_hours = self.parameters.get('detection_time_hours', 72)
        breach_vector = self.parameters.get('breach_vector', 'phishing')

        base_incident_cost = Decimal('50000')
        per_record_cost = Decimal(str(self.config['PER_RECORD_BREACH_COST']))

        self.results['direct_costs'] = (
            base_incident_cost +
            (Decimal(str(records_compromised)) * per_record_cost)
        )

        regulatory_cost = Decimal('0')
        if 'PII' in data_types or 'financial' in data_types:
            gdpr_per_record = Decimal(str(self.config['GDPR_PENALTY_PER_RECORD']))
            regulatory_cost += Decimal(str(records_compromised)) * gdpr_per_record
        if 'healthcare' in data_types:
            hipaa_per_record = Decimal(str(self.config['HIPAA_PENALTY_PER_RECORD']))
            regulatory_cost += Decimal(str(records_compromised)) * hipaa_per_record
        self.results['regulatory_costs'] = regulatory_cost

        industry = self.vendor.industry.lower()
        churn_rate = self.config['CHURN_RATES'].get(industry, 0.15)
        customers_affected = int(records_compromised * 0.1)
        customers_lost = int(customers_affected * churn_rate)
        avg_customer_value = Decimal('500')

        self.results['reputational_costs'] = Decimal(str(customers_lost)) * avg_customer_value
        self.results['customers_affected'] = customers_affected

        response_hours = detection_time_hours + 48
        hourly_cost = Decimal('250')
        self.results['operational_costs'] = Decimal(str(response_hours)) * hourly_cost

        self.results['downtime_hours'] = float(response_hours * 0.3)

        # Productivity loss: security and IT teams are pulled into incident
        # response for the full detection + response window. Loss scales with
        # how long the breach went undetected and how many records were exposed.
        # Range: ~10% (small, quick-detected breach) → 60% (large, slow-detected)
        detection_factor = min(detection_time_hours / 168, 1.0)   # normalise to 1 week
        records_factor = min(records_compromised / 100000, 1.0)   # normalise to 100k records
        self.results['productivity_loss_percentage'] = round(
            10.0 + (detection_factor * 30.0) + (records_factor * 20.0), 1
        )

        self.results['estimated_recovery_time_hours'] = round(float(
            response_hours * self.config['RECOVERY_TIME_MULTIPLIERS']['data_breach']
        ), 2)
        self.results['recovery_complexity'] = 'high' if records_compromised > 50000 else 'medium'

        affected_processes = BusinessProcess.objects.filter(
            organization=self.organization,
            dependent_vendors=self.vendor
        )
        self.results['affected_process_ids'] = [p.id for p in affected_processes]

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
                'notification_costs': float(
                    per_record_cost * Decimal(str(records_compromised)) * Decimal('0.3')
                ),
                'legal_costs': float(base_incident_cost * Decimal('0.5')),
            },
            'customer_impact': {
                'customers_affected': customers_affected,
                'estimated_churn': customers_lost,
                'churn_rate': churn_rate,
            },
        }

        logger.info(
            "Data breach impact: %d records, $%.2f",
            records_compromised,
            float(self.results['direct_costs'] + self.results['regulatory_costs']),
        )

    def _simulate_ransomware(self):
        """
        Simulate ransomware attack scenario — encryption with ransom demands.
        """
        logger.info("Simulating ransomware attack")

        ransom_amount = Decimal(str(self.parameters.get('ransom_amount', 500000)))
        downtime_hours = self.parameters.get('downtime_hours', 168)
        encryption_scope = self.parameters.get('encryption_scope', 'full')
        backup_available = self.parameters.get('backup_available', True)

        if not backup_available:
            ransom_payment_probability = 0.3
            self.results['direct_costs'] = ransom_amount * Decimal(str(ransom_payment_probability))
        else:
            self.results['direct_costs'] = Decimal('100000')

        affected_processes = BusinessProcess.objects.filter(
            organization=self.organization,
            dependent_vendors=self.vendor
        )

        total_hourly_cost = sum(
            float(p.hourly_operating_cost) for p in affected_processes
        )

        if total_hourly_cost == 0:
            hourly_cost = float(
                getattr(self.vendor, 'hourly_operating_cost', None) or Decimal('5000.00')
            )
            business_impact_factor = self.vendor.service_criticality_level / 5
            total_hourly_cost = hourly_cost * business_impact_factor

        scope_multiplier = 1.0 if encryption_scope == 'full' else 0.5
        self.results['operational_costs'] = (
            Decimal(str(total_hourly_cost)) *
            Decimal(str(downtime_hours)) *
            Decimal(str(scope_multiplier))
        )

        self.results['downtime_hours'] = float(downtime_hours)
        self.results['productivity_loss_percentage'] = (
            80.0 if encryption_scope == 'full' else 40.0
        )

        base_recovery = downtime_hours
        recovery_multiplier = 0.5 if backup_available else 2.0
        self.results['estimated_recovery_time_hours'] = round(float(
            base_recovery * recovery_multiplier *
            self.config['RECOVERY_TIME_MULTIPLIERS']['ransomware']
        ), 2)
        self.results['recovery_complexity'] = (
            'very_high' if not backup_available else 'high'
        )

        self.results['affected_process_ids'] = [p.id for p in affected_processes]

        if not backup_available:
            self.results['regulatory_costs'] = Decimal('250000')

        self.results['reputational_costs'] = Decimal('500000')

        self.results['impact_breakdown'] = {
            'ransomware_details': {
                'ransom_demanded': float(ransom_amount),
                'downtime_hours': downtime_hours,
                'encryption_scope': encryption_scope,
                'backup_available': backup_available,
            },
            'recovery_strategy': (
                'backup_restoration' if backup_available else 'potential_ransom_payment'
            ),
            'affected_systems': encryption_scope,
        }

        logger.info(
            "Ransomware impact: %dh downtime, $%.2f",
            downtime_hours,
            float(self.results['operational_costs']),
        )

    def _simulate_service_disruption(self):
        """
        Simulate service outage scenario.
        """
        logger.info("Simulating service disruption")

        duration_hours = self.parameters.get('duration_hours', 24)
        disruption_cause = self.parameters.get('disruption_cause', 'infrastructure_failure')
        customer_impact_percentage = self.parameters.get('customer_impact_percentage', 50)

        affected_processes = BusinessProcess.objects.filter(
            organization=self.organization,
            dependent_vendors=self.vendor
        )

        total_impact = Decimal('0')
        for process in affected_processes:
            criticality_multiplier = Decimal(str(process.criticality_level / 5.0))
            process_impact = (
                process.hourly_operating_cost *
                Decimal(str(duration_hours)) *
                criticality_multiplier
            )
            total_impact += process_impact

        if total_impact == 0:
            hourly_cost = getattr(self.vendor, 'hourly_operating_cost', None) or Decimal('5000.00')
            business_impact_factor = Decimal(str(self.vendor.service_criticality_level / 5))
            total_impact = Decimal(str(duration_hours)) * hourly_cost * business_impact_factor

        self.results['operational_costs'] = total_impact

        base_cost = Decimal('25000')
        complexity_multiplier = 1.5 if disruption_cause == 'cyber_attack' else 1.0
        self.results['direct_costs'] = base_cost * Decimal(str(complexity_multiplier))

        self.results['downtime_hours'] = float(duration_hours)
        self.results['productivity_loss_percentage'] = float(customer_impact_percentage)

        self.results['estimated_recovery_time_hours'] = round(float(
            duration_hours * self.config['RECOVERY_TIME_MULTIPLIERS']['service_disruption']
        ), 2)
        self.results['recovery_complexity'] = 'medium'

        sla_penalty = Decimal(str(self.vendor.contract_value)) * Decimal('0.05')
        self.results['regulatory_costs'] = sla_penalty

        if customer_impact_percentage > 70:
            self.results['reputational_costs'] = Decimal('200000')
        elif customer_impact_percentage > 40:
            self.results['reputational_costs'] = Decimal('100000')
        else:
            self.results['reputational_costs'] = Decimal('50000')

        self.results['affected_process_ids'] = [p.id for p in affected_processes]

        self.results['impact_breakdown'] = {
            'disruption_details': {
                'duration_hours': duration_hours,
                'cause': disruption_cause,
                'customer_impact_percentage': customer_impact_percentage,
            },
            'sla_penalty': float(sla_penalty),
            'affected_process_count': affected_processes.count(),
        }

        logger.info("Service disruption: %dh, $%.2f", duration_hours, float(total_impact))

    def _simulate_supply_chain_compromise(self):
        """
        Simulate supply chain attack scenario (SolarWinds-style).

        Costs are now driven by actual parameters so Monte Carlo sampling
        produces meaningful variance across iterations instead of a flat
        $3.8M every single time.
        """
        logger.info("Simulating supply chain compromise")

        affected_downstream = self.parameters.get('affected_downstream_count', 100)
        detection_delay_days = self.parameters.get('detection_delay_days', 180)
        compromise_method = self.parameters.get('compromise_method', 'build_system')
        deployment_scope = self.parameters.get('deployment_scope', 'all_customers')
        malware_type = self.parameters.get('malware_type', 'backdoor')

        # ── Direct costs ─────────────────────────────────────────────────
        # Scale with detection delay (longer dwell = more forensics/rebuild work)
        # and downstream count (more affected customers = bigger investigation)
        delay_factor = Decimal(str(min(detection_delay_days / 30, 12)))  # cap at 12× (1 year)
        downstream_factor = Decimal(str(min(affected_downstream / 100, 50)))  # cap at 50×

        base_investigation = Decimal('200000')
        self.results['direct_costs'] = (
            base_investigation
            + (delay_factor * Decimal('50000'))
            + (downstream_factor * Decimal('10000'))
        )

        # ── Operational costs ─────────────────────────────────────────────
        # Driven by how many of the org's business processes depend on this vendor
        affected_processes = BusinessProcess.objects.filter(
            organization=self.organization,
            dependent_vendors=self.vendor
        )
        total_hourly_cost = sum(
            float(p.hourly_operating_cost) for p in affected_processes
        )
        if total_hourly_cost == 0:
            hourly_cost = float(
                getattr(self.vendor, 'hourly_operating_cost', None) or Decimal('5000.00')
            )
            total_hourly_cost = hourly_cost * (self.vendor.service_criticality_level / 5)

        # Exposure window drives operational disruption
        exposure_hours = detection_delay_days * 24
        # During the dwell period, assume partial disruption (30% productivity loss)
        disruption_fraction = Decimal('0.30')
        self.results['operational_costs'] = (
            Decimal(str(total_hourly_cost))
            * Decimal(str(exposure_hours))
            * disruption_fraction
        )

        # ── Regulatory costs ──────────────────────────────────────────────
        # Notification obligations scale with downstream count
        per_entity_notification = Decimal('500')
        self.results['regulatory_costs'] = (
            Decimal(str(affected_downstream)) * per_entity_notification
        )

        # ── Reputational costs ────────────────────────────────────────────
        # Scope of deployment determines reputational blast radius
        scope_reputational = {
            'all_customers': Decimal('2000000'),
            'targeted_customers': Decimal('800000'),
            'internal_only': Decimal('200000'),
        }
        self.results['reputational_costs'] = scope_reputational.get(
            deployment_scope, Decimal('1000000')
        )

        # ── Operational metrics ───────────────────────────────────────────
        self.results['downtime_hours'] = exposure_hours * 0.1

        # Productivity loss: higher for wider deployment scope
        scope_productivity = {
            'all_customers': 40.0,
            'targeted_customers': 25.0,
            'internal_only': 15.0,
        }
        self.results['productivity_loss_percentage'] = scope_productivity.get(
            deployment_scope, 30.0
        )

        # Customers affected: proportion of org customer base that
        # experienced disruption, scaled by deployment scope
        scope_customer_fraction = {
            'all_customers': 0.60,
            'targeted_customers': 0.25,
            'internal_only': 0.05,
        }
        org_customer_base = getattr(self.organization, 'customer_base', None) or 10000
        customer_fraction = scope_customer_fraction.get(deployment_scope, 0.40)
        self.results['customers_affected'] = int(org_customer_base * customer_fraction)

        # Recovery: always long and complex for supply chain
        self.results['estimated_recovery_time_hours'] = round(float(
            720 * self.config['RECOVERY_TIME_MULTIPLIERS']['supply_chain']
        ), 2)
        self.results['recovery_complexity'] = 'very_high'

        self.results['affected_process_ids'] = [p.id for p in affected_processes]

        self.results['impact_breakdown'] = {
            'supply_chain_details': {
                'compromise_method': compromise_method,
                'detection_delay_days': detection_delay_days,
                'downstream_affected': affected_downstream,
                'deployment_scope': deployment_scope,
                'malware_type': malware_type,
                'exposure_duration_hours': exposure_hours,
            },
            'remediation_required': [
                'Full code audit',
                'System rebuilds',
                'Certificate rotation',
                'Enhanced monitoring',
                'Third-party security audit',
            ],
            'severity': 'CRITICAL',
        }

        logger.info(
            "Supply chain compromise: %d days undetected, %d downstream affected, $%.2f total",
            detection_delay_days,
            affected_downstream,
            float(
                self.results['direct_costs']
                + self.results['operational_costs']
                + self.results['regulatory_costs']
                + self.results['reputational_costs']
            ),
        )

    def _simulate_multi_vendor_failure(self):
        """
        Simulate cascading multi-vendor failure — domino effect across dependent vendors.
        """
        logger.info("Simulating multi-vendor failure")

        initial_failure_type = self.parameters.get('initial_failure_type', 'data_breach')
        cascade_probability = self.parameters.get('cascade_probability', 0.6)

        # Simulate the initial failure
        self._dispatch_scenario(initial_failure_type)

        initial_impact = (
            self.results['direct_costs'] +
            self.results['operational_costs'] +
            self.results['regulatory_costs'] +
            self.results['reputational_costs']
        )

        cascade_impacts = []

        # Vendors that this vendor depends on
        dependent_vendors = self.vendor.dependent_vendors.all()
        for dep_vendor in dependent_vendors:
            if _random.random() < cascade_probability:
                vendor_impact = self._calculate_vendor_cascade_impact(dep_vendor)
                cascade_impacts.append({
                    'vendor_id': str(dep_vendor.id),
                    'vendor_name': dep_vendor.name,
                    'impact': float(vendor_impact),
                    'reason': 'dependency_failure',
                })

        # Vendors that depend on this vendor
        depending_vendors = self.vendor.dependency_of.all()
        for dep_vendor in depending_vendors:
            if _random.random() < cascade_probability * 0.8:
                vendor_impact = self._calculate_vendor_cascade_impact(dep_vendor)
                cascade_impacts.append({
                    'vendor_id': str(dep_vendor.id),
                    'vendor_name': dep_vendor.name,
                    'impact': float(vendor_impact),
                    'reason': 'upstream_failure',
                })

        total_cascade = sum(Decimal(str(c['impact'])) for c in cascade_impacts)

        self.results['cascading_vendor_impacts'] = cascade_impacts
        self.results['total_cascading_impact'] = total_cascade

        cascade_multiplier = Decimal('1.5')
        self.results['direct_costs'] *= cascade_multiplier
        self.results['operational_costs'] *= cascade_multiplier
        self.results['recovery_complexity'] = 'very_high'

        self.results['impact_breakdown']['cascade_analysis'] = {
            'initial_failure': initial_failure_type,
            'initial_impact': float(initial_impact),
            'cascade_probability': cascade_probability,
            'vendors_affected': len(cascade_impacts),
            'total_cascade_impact': float(total_cascade),
            'cascade_multiplier': float(cascade_multiplier),
        }

        logger.info(
            "Multi-vendor failure: %d vendors affected, total $%.2f",
            len(cascade_impacts),
            float(initial_impact + total_cascade),
        )

    # ------------------------------------------------------------------
    # Impact helpers
    # ------------------------------------------------------------------

    def _calculate_vendor_cascade_impact(self, vendor: Vendor) -> Decimal:
        """Calculate impact of cascade on a dependent vendor."""
        base_impact = vendor.contract_value * Decimal('0.2')
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
        Calculate cascading impacts across vendor dependencies using CascadeAnalyzer.
        Skipped for multi_vendor — that scenario handles cascades internally.
        """
        if self.scenario_type == 'multi_vendor':
            return

        logger.info("Calculating cascading impacts")

        cascade_impacts = []
        chain = CascadeAnalyzer.trace_dependency_chain(self.vendor, max_depth=3)

        for dep_vendor, depth, multiplier in chain:
            if depth == 0:
                continue
            base_impact = self._calculate_vendor_cascade_impact(dep_vendor)
            impact = base_impact * Decimal(str(multiplier))
            cascade_impacts.append({
                'vendor_id': str(dep_vendor.id),
                'vendor_name': dep_vendor.name,
                'impact': float(impact),
                'reason': f'dependency_level_{depth}',
            })

        total_cascade = sum(Decimal(str(c['impact'])) for c in cascade_impacts)
        self.results['cascading_vendor_impacts'] = cascade_impacts
        self.results['total_cascading_impact'] = total_cascade

        if cascade_impacts:
            logger.info(
                "Cascading impact: %d vendors, $%.2f",
                len(cascade_impacts),
                float(total_cascade),
            )

    def _calculate_risk_score(self):
        """Calculate overall risk score for this simulation (0–100)."""

        total_financial = (
            self.results['direct_costs'] +
            self.results['operational_costs'] +
            self.results['regulatory_costs'] +
            self.results['reputational_costs'] +
            self.results['total_cascading_impact']
        )

        self.results['risk_score'] = RiskScoreCalculator.calculate_scenario_risk_score(
            financial_impact=total_financial,
            downtime_hours=self.results['downtime_hours'],
            recovery_complexity=self.results['recovery_complexity'],
            vendor_risk_score=self.vendor.overall_risk_score,
        )

        logger.info("Risk score calculated: %.2f/100", self.results['risk_score'])

    # ------------------------------------------------------------------
    # Monte Carlo
    # ------------------------------------------------------------------

    def _sample_parameters(self, params: dict) -> dict:
        """
        Return a copy of params with numeric values varied according to
        appropriate probability distributions.
        """

        sampled = copy.deepcopy(params)

        for key, value in sampled.items():
            if not isinstance(value, (int, float)):
                continue

            if key in ('customer_impact_percentage', 'cascade_probability'):
                if key == 'customer_impact_percentage':
                    mean = max(1, min(99, value)) / 100.0
                    sampled_val = stats.beta.rvs(mean * 10, (1 - mean) * 10) * 100
                else:
                    mean = max(0.01, min(0.99, value))
                    sampled_val = stats.beta.rvs(mean * 10, (1 - mean) * 10)

            elif key in (
                'downtime_hours', 'detection_time_hours',
                'duration_hours', 'detection_delay_days',
            ):
                v = max(1.0, float(value))
                sampled_val = stats.lognorm.rvs(s=0.3, scale=v)

            elif key in (
                'records_compromised', 'ransom_amount',
                'affected_downstream_count',
            ):
                low, high = value * 0.7, value * 1.5
                if high > low:
                    c = (value - low) / (high - low)
                    sampled_val = stats.triang.rvs(c=c, loc=low, scale=(high - low))
                else:
                    sampled_val = value
            else:
                continue

            sampled[key] = int(sampled_val) if isinstance(value, int) else float(sampled_val)

        return sampled

    def _run_monte_carlo_simulation(self):
        """
        Run Monte Carlo simulation with per-parameter independent sampling.
        Preserves the deterministic result already calculated; stores
        statistical summary in self.results['monte_carlo_results'].
        """

        iterations = self.simulation.monte_carlo_iterations
        logger.info(
            "Running Monte Carlo simulation with %d iterations", iterations
        )

        original_parameters = copy.deepcopy(self.parameters)
        original_results = copy.deepcopy(self.results)

        results_distribution = []

        for _ in range(iterations):
            self.parameters = self._sample_parameters(original_parameters)
            # Reset to a clean slate — do NOT carry over monte_carlo_results
            self.results = self._empty_results()

            self._dispatch_scenario(self.scenario_type)
            self._calculate_cascading_impacts()

            iteration_total = float(
                self.results['direct_costs'] +
                self.results['operational_costs'] +
                self.results['regulatory_costs'] +
                self.results['reputational_costs'] +
                self.results['total_cascading_impact']
            )
            results_distribution.append(iteration_total)

        # Restore original deterministic results
        self.parameters = original_parameters
        self.results = original_results

        results_array = np.array(results_distribution)

        self.results['monte_carlo_results'] = {
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
                },
            },
            'distribution': results_distribution[:100],
        }

        mc = self.results['monte_carlo_results']
        logger.info(
            "Monte Carlo complete: mean=$%.0f, 95th=$%.0f",
            mc['mean'],
            mc['percentile_95'],
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @transaction.atomic
    def _save_results(self) -> SimulationResult:
        """Save simulation results to database."""
        logger.info("Saving simulation results")

        total_impact = (
            self.results['direct_costs'] +
            self.results['operational_costs'] +
            self.results['regulatory_costs'] +
            self.results['reputational_costs'] +
            self.results['total_cascading_impact']
        )

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
            },
        )

        if self.results['affected_process_ids']:
            result.affected_processes.set(self.results['affected_process_ids'])

        logger.info("Results saved: total impact $%.2f", float(total_impact))
        return result