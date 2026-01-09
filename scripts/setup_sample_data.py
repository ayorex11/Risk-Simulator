from django.core.management.base import BaseCommand
from core.models import Organization, UserProfile
from vendors.models import Vendor
from simulations.models import ScenarioTemplate, BusinessProcess
from Account.models import CustomUser
from datetime import date, timedelta
from decimal import Decimal

def setup_sample_data():
    print("Setting up sample data...")
    
    # Get or create organization
    org, created = Organization.objects.get_or_create(
        name="Acme Corporation",
        defaults={
            'industry': 'Technology',
            'size': 'Large',
            'country': 'United States'
        }
    )
    
    
    user = CustomUser.objects.first()
    if user:
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={'organization': org, 'role': 'admin'}
        )
    
    
    scenarios = [
        {
            'scenario_type': 'data_breach',
            'name': 'Data Breach Scenario',
            'description': 'Simulates unauthorized access and data exfiltration',
            'default_parameters': {'records': 10000},
            'calculation_config': {'cost_per_record': 150}
        },
        {
            'scenario_type': 'ransomware',
            'name': 'Ransomware Attack',
            'description': 'Simulates ransomware encryption',
            'default_parameters': {'ransom': 500000},
            'calculation_config': {'downtime_multiplier': 2.0}
        }
    ]
    
    for s in scenarios:
        ScenarioTemplate.objects.get_or_create(
            scenario_type=s['scenario_type'],
            defaults=s
        )
    
    
    vendor, _ = Vendor.objects.get_or_create(
        organization=org,
        name="CloudStore Solutions",
        defaults={
            'industry': 'Cloud Services',
            'country': 'United States',
            'contact_name': 'John Smith',
            'contact_email': 'john@cloudstore.com',
            'services_provided': 'Cloud storage',
            'contract_start_date': date.today(),
            'contract_end_date': date.today() + timedelta(days=365),
            'contract_value': Decimal('500000.00'),
            'security_posture_score': 75,
            'data_sensitivity_level': 5,
            'service_criticality_level': 5,
            'created_by': user
        }
    )
    vendor.calculate_risk_score()
    
    print(" Sample data created successfully!")

if __name__ == '__main__':
    setup_sample_data()