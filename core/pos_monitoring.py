# core/pos_monitoring.py
import sentry_sdk
from decimal import Decimal
from django.utils import timezone

class POSMonitoring:
    """Custom monitoring for POS business operations"""
    
    @staticmethod
    def track_low_stock_alert(product, current_stock, threshold=10):
        """Alert when products are running low"""
        if current_stock <= threshold:
            # Set tags first
            sentry_sdk.set_tag("alert_type", "low_stock")
            sentry_sdk.set_tag("shop_id", str(product.toko.id) if product.toko else None)
            
            # Use set_extra for additional context
            sentry_sdk.set_extra("product_id", product.id)
            sentry_sdk.set_extra("product_name", product.nama)
            sentry_sdk.set_extra("current_stock", float(current_stock))
            sentry_sdk.set_extra("threshold", threshold)
            sentry_sdk.set_extra("shop_id", product.toko.id if product.toko else None)
            sentry_sdk.set_extra("category", product.kategori.nama if product.kategori else None)
            sentry_sdk.set_extra("business_impact", "medium")
            sentry_sdk.set_extra("action_needed", "restock_soon")
            
            # Capture message without extras parameter
            sentry_sdk.capture_message(
                f"🚨 LOW STOCK: {product.nama} - Only {current_stock} left!",
                level="warning"
            )
    
    @staticmethod
    def track_large_transaction(transaction_amount, shop_name, user_name, threshold=500000):
        """Track unusually large transactions"""
        if transaction_amount >= threshold:
            # Set tags first
            sentry_sdk.set_tag("alert_type", "large_transaction")
            sentry_sdk.set_tag("transaction_size", "large")
            
            # Use set_extra for additional context
            sentry_sdk.set_extra("transaction_amount", float(transaction_amount))
            sentry_sdk.set_extra("threshold", float(threshold))
            sentry_sdk.set_extra("shop_name", shop_name)
            sentry_sdk.set_extra("staff_member", user_name)
            sentry_sdk.set_extra("timestamp", timezone.now().isoformat())
            sentry_sdk.set_extra("business_impact", "high" if transaction_amount > 1000000 else "medium")
            sentry_sdk.set_extra("needs_verification", transaction_amount > 1000000)
            
            # Capture message without extras parameter
            sentry_sdk.capture_message(
                f"💰 LARGE TRANSACTION: Rp {transaction_amount:,.0f} at {shop_name}",
                level="info"
            )
    
    @staticmethod
    def track_failed_operation(operation_type, error_msg, user_id=None, shop_id=None, **extra_context):
        """Track failed business operations"""
        # Set tags first
        sentry_sdk.set_tag("alert_type", "operation_failed")
        sentry_sdk.set_tag("operation", operation_type)
        sentry_sdk.set_tag("shop_id", str(shop_id) if shop_id else None)
        
        # Use set_extra for additional context
        sentry_sdk.set_extra("operation_type", operation_type)
        sentry_sdk.set_extra("error_message", error_msg)
        sentry_sdk.set_extra("user_id", user_id)
        sentry_sdk.set_extra("shop_id", shop_id)
        sentry_sdk.set_extra("timestamp", timezone.now().isoformat())
        sentry_sdk.set_extra("business_impact", "high")
        
        # Add extra context
        for key, value in extra_context.items():
            sentry_sdk.set_extra(key, value)
        
        # Capture message without extras parameter
        sentry_sdk.capture_message(
            f"❌ {operation_type.upper()} FAILED: {error_msg}",
            level="error"
        )
    
    @staticmethod
    def track_business_success(operation_type, shop_name, user_name, **extra_context):
        """Track successful business operations for insights"""
        # Set tags first
        sentry_sdk.set_tag("event_type", "business_success")
        sentry_sdk.set_tag("operation", operation_type)
        
        # Use set_extra for additional context
        sentry_sdk.set_extra("operation_type", operation_type)
        sentry_sdk.set_extra("shop_name", shop_name)
        sentry_sdk.set_extra("staff_member", user_name)
        sentry_sdk.set_extra("timestamp", timezone.now().isoformat())
        
        # Add extra context
        for key, value in extra_context.items():
            sentry_sdk.set_extra(key, value)
        
        # Capture message without extras parameter
        sentry_sdk.capture_message(
            f"✅ {operation_type.upper()} SUCCESS at {shop_name}",
            level="info"
        )