from django.contrib import admin
from .models import FinancialReport, CategorySummary, MonthlySummary

class CategorySummaryInline(admin.TabularInline):
    model = CategorySummary
    extra = 0

class MonthlySummaryInline(admin.TabularInline):
    model = MonthlySummary
    extra = 0

@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'start_date', 'end_date', 'total_income', 'total_expense', 'total_profit', 'created_at']
    inlines = [CategorySummaryInline, MonthlySummaryInline]
