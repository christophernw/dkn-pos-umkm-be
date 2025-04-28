from django.urls import path
from .views import FinancialReportView

urlpatterns = [
    path('reports/financial/', FinancialReportView.as_view(), name='financial_report'),
]