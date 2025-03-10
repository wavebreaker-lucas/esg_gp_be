from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import CustomUser, LayerProfile, AppUser
from accounts.serializers.models import LayerProfileSerializer

class UserFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create creator user
        self.creator_data = {
            'email': 'creator@test.com',
            'password': 'TestPass123!',
            'role': 'CREATOR'
        }
        self.creator = CustomUser.objects.create_user(**self.creator_data)
        
        # Create layer profile
        self.layer_data = {
            'name': 'Test Company',
            'type': 'GROUP',
            'creator': self.creator
        }
        self.layer = LayerProfile.objects.create(**self.layer_data)
        
    def test_user_registration_flow(self):
        """Test complete user registration flow"""
        # 1. Register new user
        register_data = {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'role': 'MANAGEMENT',
            'layer': self.layer.id
        }
        
        response = self.client.post(
            reverse('register-layer-profile'),
            register_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 2. Test login
        login_data = {
            'email': 'test@example.com',
            'password': 'SecurePass123!'
        }
        response = self.client.post(
            reverse('token_obtain_pair'),
            login_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
        # Store token for authenticated requests
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # 3. Test profile access
        response = self.client.get(
            reverse('layer-profile-detail', kwargs={'pk': self.layer.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_layer_hierarchy(self):
        """Test layer creation and hierarchy"""
        self.client.force_authenticate(user=self.creator)
        
        # Create subsidiary
        subsidiary_data = {
            'name': 'Test Subsidiary',
            'type': 'SUBSIDIARY',
            'parent': self.layer.id
        }
        response = self.client.post(
            reverse('layer-profile-list'),
            subsidiary_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify hierarchy
        response = self.client.get(
            reverse('layer-profile-detail', kwargs={'pk': response.data['id']})
        )
        self.assertEqual(response.data['parent'], self.layer.id)
        
    def test_role_permissions(self):
        """Test role-based permissions"""
        # Create operation user
        operation_user = CustomUser.objects.create_user(
            email='operation@test.com',
            password='TestPass123!',
            role='OPERATION'
        )
        
        # Try to create layer (should fail)
        self.client.force_authenticate(user=operation_user)
        layer_data = {
            'name': 'Unauthorized Layer',
            'type': 'GROUP'
        }
        response = self.client.post(
            reverse('layer-profile-list'),
            layer_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 