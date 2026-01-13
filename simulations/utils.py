from decimal import Decimal
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger('simulations')


class ImpactCalculator:
    """
    Utility class for impact calculations
    """
    
    @staticmethod
    def calculate_downtime_cost(
        hourly_cost: Decimal,
        hours: float,
        criticality_multiplier: float = 1.0
    ) -> Decimal:
        """
        Calculate cost of downtime
        """
        return (
            hourly_cost * 
            Decimal(str(hours)) * 
            Decimal(str(criticality_multiplier))
        )
    
    @staticmethod
    def calculate_data_breach_cost(
        records: int,
        per_record_cost: Decimal,
        has_sensitive_data: bool = True
    ) -> Decimal:
        """
        Calculate data breach costs
        """
        base_cost = Decimal(str(records)) * per_record_cost
        
        if has_sensitive_data:
            base_cost *= Decimal('1.5')  # 50% premium for sensitive data
        
        return base_cost
    
    @staticmethod
    def calculate_regulatory_penalty(
        records: int,
        regulation_type: str
    ) -> Decimal:
        """
        Calculate regulatory penalties
        """
        penalties = {
            'gdpr': Decimal('4'),      # €4 per record
            'hipaa': Decimal('250'),   # $250 per record
            'pci_dss': Decimal('50000'),  # Flat fine
            'ccpa': Decimal('7.50'),   # $7.50 per record
        }
        
        if regulation_type == 'pci_dss':
            return penalties['pci_dss']
        
        per_record = penalties.get(regulation_type.lower(), Decimal('5'))
        return Decimal(str(records)) * per_record
    
    @staticmethod
    def calculate_customer_churn_cost(
        customers_affected: int,
        churn_rate: float,
        avg_customer_lifetime_value: Decimal
    ) -> Decimal:
        """
        Calculate cost of customer churn
        """
        customers_lost = int(customers_affected * churn_rate)
        return Decimal(str(customers_lost)) * avg_customer_lifetime_value
    
    @staticmethod
    def estimate_recovery_time(
        base_hours: float,
        complexity: str,
        resources_available: bool = True
    ) -> float:
        """
        Estimate recovery time
        """
        complexity_multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5,
            'very_high': 2.0,
        }
        
        multiplier = complexity_multipliers.get(complexity, 1.0)
        
        if not resources_available:
            multiplier *= 1.5
        
        return base_hours * multiplier
    
    @staticmethod
    def calculate_productivity_loss(
        hourly_operating_cost: Decimal,
        downtime_hours: float,
        productivity_loss_percentage: float
    ) -> Decimal:
        """
        Calculate productivity loss costs
        """
        return (
            hourly_operating_cost * 
            Decimal(str(downtime_hours)) * 
            Decimal(str(productivity_loss_percentage / 100))
        )


class RiskScoreCalculator:
    """
    Calculate risk scores for various scenarios
    """
    
    @staticmethod
    def calculate_scenario_risk_score(
        financial_impact: Decimal,
        downtime_hours: float,
        recovery_complexity: str,
        vendor_risk_score: float
    ) -> float:
        """
        Calculate overall risk score for a scenario
        """
        import math
        
        # Financial impact score (0-40)
        if financial_impact > 0:
            financial_score = min(40, 10 + (10 * math.log10(float(financial_impact) / 100000)))
        else:
            financial_score = 0
        
        # Downtime score (0-30)
        downtime_score = min(30, downtime_hours / 5)
        
        # Complexity score (0-15)
        complexity_scores = {
            'low': 3,
            'medium': 7,
            'high': 11,
            'very_high': 15,
        }
        complexity_score = complexity_scores.get(recovery_complexity, 7)
        
        # Vendor risk component (0-15)
        vendor_component = min(15, vendor_risk_score / 100 * 15)
        
        total = financial_score + downtime_score + complexity_score + vendor_component
        
        return min(100, total)
    
    @staticmethod
    def categorize_risk_score(score: float) -> str:
        """
        Categorize risk score into levels
        """
        if score >= 75:
            return 'critical'
        elif score >= 50:
            return 'high'
        elif score >= 25:
            return 'medium'
        else:
            return 'low'


class CascadeAnalyzer:
    """
    Analyze cascading failures across vendor dependencies
    """
    
    @staticmethod
    def trace_dependency_chain(
        vendor,
        max_depth: int = 5,
        visited: set = None
    ) -> List[Tuple]:
        """
        Trace vendor dependency chain
        Returns list of (vendor, depth, impact_multiplier) tuples
        """
        if visited is None:
            visited = set()
        
        chain = []
        
        if vendor.id in visited or max_depth <= 0:
            return chain
        
        visited.add(vendor.id)
        chain.append((vendor, 0, 1.0))
        
        # Recursive trace through dependencies
        for dep_vendor in vendor.dependent_vendors.all():
            if dep_vendor.id not in visited:
                # Impact decreases with depth
                impact_multiplier = 0.8 ** 1  # 80% impact per level
                chain.append((dep_vendor, 1, impact_multiplier))
                
                # Recursively trace
                sub_chain = CascadeAnalyzer.trace_dependency_chain(
                    dep_vendor,
                    max_depth - 1,
                    visited
                )
                
                for sub_vendor, sub_depth, sub_multiplier in sub_chain:
                    if sub_vendor.id != dep_vendor.id:
                        chain.append((
                            sub_vendor,
                            sub_depth + 1,
                            sub_multiplier * impact_multiplier
                        ))
        
        return chain
    
    @staticmethod
    def calculate_cascade_probability(
        vendor_risk_level: str,
        failure_type: str
    ) -> float:
        """
        Calculate probability of cascade
        """
        # Base probabilities by risk level
        base_probabilities = {
            'low': 0.2,
            'medium': 0.4,
            'high': 0.6,
            'critical': 0.8,
        }
        
        # Multipliers by failure type
        failure_multipliers = {
            'data_breach': 0.8,
            'ransomware': 1.2,
            'service_disruption': 1.0,
            'supply_chain': 1.5,
        }
        
        base_prob = base_probabilities.get(vendor_risk_level, 0.5)
        multiplier = failure_multipliers.get(failure_type, 1.0)
        
        return min(1.0, base_prob * multiplier)


class MonteCarloSimulator:
    """
    Monte Carlo simulation utilities
    """
    
    @staticmethod
    def run_iterations(
        baseline_value: float,
        iterations: int,
        variance: float = 0.15
    ) -> Dict:
        """
        Run Monte Carlo iterations
        
        Args:
            baseline_value: Base value to vary
            iterations: Number of iterations
            variance: Standard deviation as percentage (0.15 = 15%)
        
        Returns:
            Dictionary with statistical results
        """
        import numpy as np
        
        # Generate random variations using normal distribution
        variations = np.random.normal(1.0, variance, iterations)
        
        # Clip extreme values (±3 standard deviations)
        variations = np.clip(variations, 1.0 - 3*variance, 1.0 + 3*variance)
        
        # Calculate results
        results = variations * baseline_value
        
        return {
            'mean': float(np.mean(results)),
            'median': float(np.median(results)),
            'std_dev': float(np.std(results)),
            'min': float(np.min(results)),
            'max': float(np.max(results)),
            'percentiles': {
                10: float(np.percentile(results, 10)),
                25: float(np.percentile(results, 25)),
                50: float(np.percentile(results, 50)),
                75: float(np.percentile(results, 75)),
                90: float(np.percentile(results, 90)),
                95: float(np.percentile(results, 95)),
                99: float(np.percentile(results, 99)),
            },
            'confidence_intervals': {
                '90': {
                    'lower': float(np.percentile(results, 5)),
                    'upper': float(np.percentile(results, 95)),
                },
                '95': {
                    'lower': float(np.percentile(results, 2.5)),
                    'upper': float(np.percentile(results, 97.5)),
                },
                '99': {
                    'lower': float(np.percentile(results, 0.5)),
                    'upper': float(np.percentile(results, 99.5)),
                }
            },
            'distribution_sample': results[:100].tolist()  # First 100 for visualization
        }
    
    @staticmethod
    def analyze_risk_distribution(
        monte_carlo_results: Dict
    ) -> Dict:
        """
        Analyze risk distribution from Monte Carlo results
        """
        percentile_95 = monte_carlo_results['percentiles'][95]
        mean = monte_carlo_results['mean']
        
        # Value at Risk (VaR)
        var_95 = percentile_95
        
        # Conditional Value at Risk (CVaR) - average of values above VaR
        # Approximate as 1.3x the 95th percentile
        cvar_95 = percentile_95 * 1.3
        
        # Risk categories
        if percentile_95 > mean * 1.5:
            risk_profile = 'high_variance'
        elif percentile_95 > mean * 1.2:
            risk_profile = 'moderate_variance'
        else:
            risk_profile = 'low_variance'
        
        return {
            'value_at_risk_95': var_95,
            'conditional_var_95': cvar_95,
            'risk_profile': risk_profile,
            'worst_case_scenario': monte_carlo_results['percentiles'][99],
            'best_case_scenario': monte_carlo_results['percentiles'][10],
            'most_likely': monte_carlo_results['median'],
        }


class ReportGenerator:
    """
    Generate simulation reports and summaries
    """
    
    @staticmethod
    def generate_executive_summary(simulation_result) -> Dict:
        """
        Generate executive summary from simulation result
        """
        total_impact = float(simulation_result.total_financial_impact)
        
        # Format large numbers
        if total_impact >= 1_000_000:
            impact_str = f"${total_impact/1_000_000:.1f}M"
        elif total_impact >= 1_000:
            impact_str = f"${total_impact/1_000:.0f}K"
        else:
            impact_str = f"${total_impact:.0f}"
        
        # Key findings
        findings = []
        
        if simulation_result.total_financial_impact > 1_000_000:
            findings.append("⚠️ Financial impact exceeds $1 million - immediate mitigation required")
        
        if simulation_result.downtime_hours > 48:
            findings.append(f"⚠️ Extended downtime of {simulation_result.downtime_hours:.0f} hours expected")
        
        if simulation_result.recovery_complexity in ['high', 'very_high']:
            findings.append("⚠️ Complex recovery process - specialized expertise required")
        
        if len(simulation_result.cascading_vendor_impacts) > 0:
            findings.append(f"⚠️ {len(simulation_result.cascading_vendor_impacts)} dependent vendors affected")
        
        # Recommendations
        recommendations = ReportGenerator._generate_recommendations(simulation_result)
        
        return {
            'total_impact': impact_str,
            'risk_score': f"{simulation_result.risk_score:.0f}/100",
            'recovery_time': f"{simulation_result.estimated_recovery_time_hours:.0f} hours",
            'key_findings': findings,
            'recommendations': recommendations,
            'affected_processes': simulation_result.affected_processes.count(),
        }
    
    @staticmethod
    def _generate_recommendations(simulation_result) -> List[str]:
        """
        Generate recommendations based on simulation results
        """
        recommendations = []
        
        # Financial impact recommendations
        if simulation_result.direct_costs > 500_000:
            recommendations.append("Consider cyber insurance to cover direct incident costs")
        
        if simulation_result.regulatory_costs > 100_000:
            recommendations.append("Strengthen compliance controls to minimize regulatory exposure")
        
        # Operational recommendations
        if simulation_result.downtime_hours > 24:
            recommendations.append("Implement business continuity plan with alternate vendor options")
        
        if simulation_result.recovery_complexity == 'very_high':
            recommendations.append("Establish incident response retainer with specialized security firm")
        
        # Cascading impact recommendations
        if len(simulation_result.cascading_vendor_impacts) > 2:
            recommendations.append("Reduce vendor dependencies or implement redundancy")
        
        # Process recommendations
        critical_processes = simulation_result.affected_processes.filter(criticality_level__gte=4)
        if critical_processes.exists():
            recommendations.append("Critical processes affected - establish backup service providers")
        
        return recommendations[:5]  # Top 5 recommendations