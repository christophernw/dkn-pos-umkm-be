import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import importlib

class TestASGI(unittest.TestCase):
    
    @patch('os.environ.setdefault')
    def test_django_settings_module_set(self, mock_setdefault):
        """Test that the DJANGO_SETTINGS_MODULE environment variable is set correctly."""
        # Force reload the module to trigger the code in the module
        if 'backend.asgi' in sys.modules:
            del sys.modules['backend.asgi']
        
        import backend.asgi
        
        # Verify that setdefault was called with the correct arguments
        mock_setdefault.assert_called_once_with('DJANGO_SETTINGS_MODULE', 'backend.settings')
    
    @patch('django.core.asgi.get_asgi_application')
    def test_get_asgi_application_called(self, mock_get_asgi_application):
        """Test that get_asgi_application is called."""
        # Create a mock application
        mock_application = MagicMock()
        mock_get_asgi_application.return_value = mock_application
        
        # Force reload the module
        if 'backend.asgi' in sys.modules:
            del sys.modules['backend.asgi']
        
        import backend.asgi
        
        # Verify get_asgi_application was called
        mock_get_asgi_application.assert_called_once()
        
        # Verify the application was set to the return value
        self.assertEqual(backend.asgi.application, mock_application)
    
    @patch('django.core.asgi.get_asgi_application')
    def test_application_is_created(self, mock_get_asgi_application):
        """Test that the application variable is set correctly."""
        # Create a mock application with a specific attribute for verification
        mock_application = MagicMock()
        mock_application.test_attribute = "test_value"
        mock_get_asgi_application.return_value = mock_application
        
        import backend.asgi
        
        # Verify the application has the expected attributes from our mock
        self.assertEqual(backend.asgi.application.test_attribute, "test_value")
        
class TestWSGI(unittest.TestCase):
    
    @patch('os.environ.setdefault')
    def test_django_settings_module_set(self, mock_setdefault):
        """Test that the DJANGO_SETTINGS_MODULE environment variable is set correctly."""
        
        import backend.wsgi
        
        # Verify that setdefault was called with the correct arguments
        mock_setdefault.assert_called_once_with('DJANGO_SETTINGS_MODULE', 'backend.settings')
    
    @patch('django.core.wsgi.get_wsgi_application')
    def test_get_wsgi_application_called(self, mock_get_wsgi_application):
        """Test that get_wsgi_application is called."""
        # Create a mock application
        mock_application = MagicMock()
        mock_get_wsgi_application.return_value = mock_application
        
        # Force reload the module
        if 'backend.wsgi' in sys.modules:
            del sys.modules['backend.wsgi']
        
        import backend.wsgi
        
        # Verify that the application is set correctly
        self.assertEqual(backend.wsgi.application, mock_application)
