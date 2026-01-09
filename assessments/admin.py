from django.contrib import admin
from .models import VendorAssessment, AssessmentQuestion, AssessmentTemplate

@admin.register(VendorAssessment)
class VendorAssessmentAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'assessment_date', 'status', 'overall_score', 'assessed_by']
    list_filter = ['status', 'assessment_type', 'assessment_date']
    search_fields = ['vendor__name']

@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'category', 'framework', 'is_active']
    list_filter = ['category', 'framework', 'is_active']

@admin.register(AssessmentTemplate)
class AssessmentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'framework', 'is_default', 'is_active']
    list_filter = ['framework', 'is_active']