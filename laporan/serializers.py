from rest_framework import serializers
from .models import FinancialReport, CategorySummary, MonthlySummary

class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorySummary
        fields = ['category_name', 'amount', 'percentage']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Match frontend expected field name
        representation['category'] = representation.pop('category_name')
        return representation

class MonthlySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlySummary
        fields = ['month', 'income', 'expense', 'profit']

class FinancialReportSerializer(serializers.ModelSerializer):
    income_by_category = serializers.SerializerMethodField()
    expense_by_category = serializers.SerializerMethodField()
    monthly_data = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    
    class Meta:
        model = FinancialReport
        fields = ['summary', 'income_by_category', 'expense_by_category', 'monthly_data']
    
    def get_summary(self, obj):
        return {
            'total_income': obj.total_income,
            'total_expense': obj.total_expense,
            'total_profit': obj.total_profit,
            'transaction_count': obj.transaction_count
        }
    
    def get_income_by_category(self, obj):
        income_categories = obj.categories.filter(category_type='income')
        return CategorySummarySerializer(income_categories, many=True).data
    
    def get_expense_by_category(self, obj):
        expense_categories = obj.categories.filter(category_type='expense')
        return CategorySummarySerializer(expense_categories, many=True).data
    
    def get_monthly_data(self, obj):
        monthly_data = obj.monthly_data.all().order_by('month')
        return MonthlySummarySerializer(monthly_data, many=True).data