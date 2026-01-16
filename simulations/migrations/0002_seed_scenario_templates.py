from django.db import migrations


def seed_scenario_templates(apps, schema_editor):
    """Seed initial scenario templates"""
    ScenarioTemplate = apps.get_model('simulations', 'ScenarioTemplate')
    
    templates = [
        {
            'scenario_type': 'data_breach',
            'name': 'Data Breach Simulation',
            'description': 'Simulate unauthorized access and data exfiltration incidents. Models the impact of compromised customer data, intellectual property theft, or credential leaks through various attack vectors.',
            'default_parameters': {
                'records_compromised': 10000,
                'data_types': ['PII'],
                'detection_time_hours': 72,
                'breach_vector': 'phishing',
                'attacker_dwell_time_days': 30
            },
            'calculation_config': {
                'per_record_cost': 150,
                'base_incident_cost': 50000,
                'gdpr_penalty_per_record': 4,
                'hipaa_penalty_per_record': 250,
                'churn_rates': {
                    'technology': 0.15,
                    'healthcare': 0.20,
                    'financial': 0.25,
                    'retail': 0.18,
                    'manufacturing': 0.12,
                    'default': 0.15
                },
                'recovery_time_multiplier': 1.5
            },
            'is_active': True,
            'version': '1.0'
        },
        {
            'scenario_type': 'ransomware',
            'name': 'Ransomware Attack Simulation',
            'description': 'Simulate ransomware encryption attacks with ransom demands. Models system encryption, operational downtime, ransom payment decisions, and recovery complexity with or without backups.',
            'default_parameters': {
                'ransom_amount': 500000,
                'downtime_hours': 168,
                'encryption_scope': 'full',
                'backup_available': True,
                'restoration_difficulty': 'medium'
            },
            'calculation_config': {
                'base_restoration_cost': 100000,
                'ransom_payment_probability_no_backup': 0.30,
                'recovery_time_multiplier': 2.0,
                'backup_recovery_multiplier': 0.5,
                'no_backup_recovery_multiplier': 2.0,
                'reputational_damage_base': 500000
            },
            'is_active': True,
            'version': '1.0'
        },
        {
            'scenario_type': 'service_disruption',
            'name': 'Service Disruption Simulation',
            'description': 'Simulate service outages and availability incidents. Models infrastructure failures, cyber attacks, natural disasters, or third-party failures causing service unavailability and operational impact.',
            'default_parameters': {
                'duration_hours': 24,
                'disruption_cause': 'infrastructure_failure',
                'affected_services': ['primary'],
                'customer_impact_percentage': 50,
                'sla_breach': False
            },
            'calculation_config': {
                'base_investigation_cost': 25000,
                'cyber_attack_multiplier': 1.5,
                'sla_penalty_rate': 0.05,
                'recovery_time_multiplier': 1.2,
                'reputational_cost_tiers': {
                    'low': 50000,
                    'medium': 100000,
                    'high': 200000
                }
            },
            'is_active': True,
            'version': '1.0'
        },
        {
            'scenario_type': 'supply_chain',
            'name': 'Supply Chain Compromise Simulation',
            'description': 'Simulate supply chain attacks (SolarWinds-style). Models malicious code injection in vendor software, widespread downstream impact, extended detection delays, and complex remediation requirements.',
            'default_parameters': {
                'compromise_method': 'build_system',
                'deployment_scope': 'all_customers',
                'detection_delay_days': 180,
                'affected_downstream_count': 100,
                'malware_type': 'backdoor'
            },
            'calculation_config': {
                'base_investigation_cost': 1000000,
                'organizational_response_cost': 500000,
                'regulatory_notification_cost': 300000,
                'reputational_damage_base': 2000000,
                'recovery_time_multiplier': 3.0,
                'base_recovery_days': 30,
                'detection_delay_impact_multiplier': 0.1
            },
            'is_active': True,
            'version': '1.0'
        },
        {
            'scenario_type': 'multi_vendor',
            'name': 'Multi-Vendor Cascading Failure Simulation',
            'description': 'Simulate cascading failures across vendor dependencies. Models domino effects where initial vendor failure triggers downstream and upstream vendor impacts based on dependency relationships.',
            'default_parameters': {
                'initial_failure_type': 'service_disruption',
                'cascade_probability': 0.6,
                'max_cascade_depth': 3,
                'simultaneous_failures': 1,
                'recovery_coordination': 'partial'
            },
            'calculation_config': {
                'cascade_impact_rate': 0.20,
                'cascade_multiplier': 1.5,
                'risk_level_multipliers': {
                    'low': 0.5,
                    'medium': 1.0,
                    'high': 1.5,
                    'critical': 2.0
                },
                'recovery_time_multiplier': 2.5,
                'coordination_multipliers': {
                    'none': 1.5,
                    'partial': 1.0,
                    'full': 0.7
                }
            },
            'is_active': True,
            'version': '1.0'
        }
    ]
    
    for template_data in templates:
        ScenarioTemplate.objects.get_or_create(
            scenario_type=template_data['scenario_type'],
            defaults=template_data
        )


def reverse_seed(apps, schema_editor):
    """Remove seeded scenario templates"""
    ScenarioTemplate = apps.get_model('simulations', 'ScenarioTemplate')
    ScenarioTemplate.objects.filter(
        scenario_type__in=[
            'data_breach',
            'ransomware', 
            'service_disruption',
            'supply_chain',
            'multi_vendor'
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('simulations', '0001_initial'),  # Update this to match your actual previous migration
    ]

    operations = [
        migrations.RunPython(seed_scenario_templates, reverse_seed),
    ]