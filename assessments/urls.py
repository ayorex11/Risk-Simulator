from django.urls import path
from . import views

app_name = 'assessments'

urlpatterns = [
    path('', views.assessment_list_create, name='assessment-list-create'),
    path('<uuid:assessment_id>/', views.assessment_detail, name='assessment-detail'),
    path('<uuid:assessment_id>/approve/', views.approve_assessment, name='approve-assessment'),
    path('<uuid:assessment_id>/compare/', views.compare_assessments, name='compare-assessments'),
    path('summary/', views.assessment_summary, name='assessment-summary'),
    path('questions/', views.question_list_create, name='question-list-create'),
    path('questionnaire/', views.get_questionnaire_template, name='questionnaire-template'),
    path('templates/', views.template_list_create, name='template-list-create'),
    path('templates/<uuid:template_id>/', views.template_detail, name='template-detail'),
    path('<uuid:assessment_id>/evidence/', views.evidence_list_create, name='evidence-list-create'),
    path('evidence/<uuid:evidence_id>/', views.evidence_delete, name='evidence-delete'),
]