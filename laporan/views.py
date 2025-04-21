from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum, Count
from transaksi.models import Transaksi  # Assuming you have this model
from .models import FinancialReport, CategorySummary, MonthlySummary
from .serializers import FinancialReportSerializer
from ninja import Router

laporan_router = Router()


class FinancialReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response({"error": "start_date and end_date query parameters are required"}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create report
        report = self._generate_financial_report(request.user, start_date, end_date)
        serializer = FinancialReportSerializer(report)
        
        return Response(serializer.data)
    
    def _generate_financial_report(self, user, start_date, end_date):
        # Create a new report instance
        report = FinancialReport.objects.create(
            start_date=start_date,
            end_date=end_date
        )
        
        # Query transactions for the date range
        # Assumes transactions have 'user', 'date', 'type' (income/expense), 'amount', 'category' fields
        transactions = Transaksi.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date
        )
        
        # Calculate summary
        income_transactions = transactions.filter(type='income')
        expense_transactions = transactions.filter(type='expense')
        
        total_income = income_transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        total_expense = expense_transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        total_profit = total_income - total_expense
        transaction_count = transactions.count()
        
        report.total_income = total_income
        report.total_expense = total_expense
        report.total_profit = total_profit
        report.transaction_count = transaction_count
        report.save()
        
        # Process income by category
        self._process_category_summary(report, income_transactions, 'income')
        
        # Process expense by category
        self._process_category_summary(report, expense_transactions, 'expense')
        
        # Process monthly data
        self._process_monthly_data(report, transactions, start_date, end_date)
        
        return report
    
    def _process_category_summary(self, report, transactions, category_type):
        total = transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)
        
        if total > 0:
            category_summary = transactions.values('category').annotate(
                total_amount=Sum('amount')
            )
            
            for item in category_summary:
                amount = item['total_amount']
                percentage = (amount / total) * 100 if total else 0
                
                CategorySummary.objects.create(
                    report=report,
                    category_type=category_type,
                    category_name=item['category'],
                    amount=amount,
                    percentage=percentage
                )
    
    def _process_monthly_data(self, report, transactions, start_date, end_date):
        # Group transactions by month
        # This is simplified - you would need a proper implementation based on your data structure
        
        # Dummy implementation for placeholder purposes
        months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                  "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        current_date = datetime.now().date()
        current_month = current_date.month
        current_year = current_date.year
        
        # Create monthly data for the last 4 months
        for i in range(4):
            month_index = (current_month - i - 1) % 12
            year = current_year if month_index < current_month else current_year - 1
            month_name = f"{months[month_index]} {year}"
            
            # In a real implementation, you would filter transactions for this month
            # and calculate actual sums
            
            MonthlySummary.objects.create(
                report=report,
                month=month_name,
                income=Decimal(1000000 + (i * 100000)),  # Placeholder values
                expense=Decimal(600000 + (i * 75000)),
                profit=Decimal(400000 + (i * 25000))
            )