from django.db import models

class FinancialReport(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expense = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transaction_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Financial Report {self.start_date} to {self.end_date}"

class CategorySummary(models.Model):
    CATEGORY_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    report = models.ForeignKey(FinancialReport, on_delete=models.CASCADE, related_name='categories')
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPE_CHOICES)
    category_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    def __str__(self):
        return f"{self.category_name} ({self.get_category_type_display()})"

class MonthlySummary(models.Model):
    report = models.ForeignKey(FinancialReport, on_delete=models.CASCADE, related_name='monthly_data')
    month = models.CharField(max_length=20)  # Format: "January 2023"
    income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    expense = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.month} Summary"