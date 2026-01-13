from django.urls import path
from . import views

app_name = 'simulations'

urlpatterns = [
    path('processes/', views.process_list_create, name='process-list-create'),
    path('processes/<uuid:process_id>/', views.process_detail, name='process-detail'),
    path('scenarios/', views.scenario_template_list, name='scenario-list'),
    path('scenarios/<uuid:template_id>/', views.scenario_template_detail, name='scenario-detail'),
    path('scenarios/<uuid:template_id>/parameters/', views.scenario_parameters, name='scenario-parameters'),
    path('', views.simulation_list_create, name='simulation-list-create'),
    path('<uuid:simulation_id>/', views.simulation_detail, name='simulation-detail'),
    path('<uuid:simulation_id>/execute/', views.execute_simulation, name='execute-simulation'),
    path('<uuid:simulation_id>/results/', views.result_detail, name='simulation-results'),
    path('what-if/', views.what_if_analysis, name='what-if-analysis'),
    path('compare/', views.compare_simulations, name='compare-simulations'),
    path('summary/', views.simulation_summary, name='simulation-summary'),
    path('batch-create/', views.batch_create_simulations, name='batch-create'),
]