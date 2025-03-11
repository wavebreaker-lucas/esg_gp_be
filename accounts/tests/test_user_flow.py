from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import CustomUser, LayerProfile, AppUser
from accounts.serializers.models import LayerProfileSerializer

class UserFlowTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create Baker Tilly admin
        self.admin_data = {
            'email': 'admin@bakertilly.com',
            'password': 'TestPass123!',
            'is_baker_tilly_admin': True
        }
        self.admin = CustomUser.objects.create_user(**self.admin_data)
        
        # Create company and initial admin
        self.company_data = {
            'company_name': 'Test Company',
            'industry': 'Technology',
            'location': 'Hong Kong',
            'admin_email': 'creator@test.com',
            'admin_name': 'Test Creator',
            'admin_title': 'ESG Director'
        }
        
    def test_client_setup_flow(self):
        """Test complete client setup and user management flow"""
        # 1. Baker Tilly admin creates company and admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('client-setup'),
            self.company_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 2. Company admin can login
        login_data = {
            'email': self.company_data['admin_email'],
            'password': response.data['admin_password']  # Password sent in response
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
            reverse('layer-profile-detail', kwargs={'pk': 1})  # First group layer
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_layer_hierarchy(self):
        """Test layer creation and hierarchy"""
        # First create company and get admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('client-setup'),
            self.company_data,
            format='json'
        )
        creator = CustomUser.objects.get(email=self.company_data['admin_email'])
        group_layer_id = response.data['group_layer']['id']
        
        # Login as company admin
        self.client.force_authenticate(user=creator)
        
        # Create subsidiary
        subsidiary_data = {
            'layer_type': 'SUBSIDIARY',
            'company_name': 'Test Subsidiary',
            'company_industry': 'Software',
            'company_location': 'Singapore',
            'shareholding_ratio': 100.00,
            'group_id': group_layer_id
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
        self.assertEqual(response.data['group_id'], group_layer_id)
        
    def test_role_permissions(self):
        """Test role-based permissions"""
        # First create company and get admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse('client-setup'),
            self.company_data,
            format='json'
        )
        group_layer_id = response.data['group_layer']['id']
        
        # Create operation user through company admin
        operation_data = {
            'email': 'operation@test.com',
            'name': 'Test Operation',
            'title': 'Staff',
            'role': 'OPERATION'
        }
        
        creator = CustomUser.objects.get(email=self.company_data['admin_email'])
        self.client.force_authenticate(user=creator)
        
        response = self.client.post(
            reverse('app-user-add-user', kwargs={'pk': group_layer_id}),
            operation_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Try to create layer as operation user (should fail)
        operation_user = CustomUser.objects.get(email='operation@test.com')
        self.client.force_authenticate(user=operation_user)
        
        layer_data = {
            'layer_type': 'SUBSIDIARY',
            'company_name': 'Unauthorized Layer',
            'company_industry': 'Technology',
            'company_location': 'Singapore',
            'shareholding_ratio': 100.00,
            'group_id': group_layer_id
        }
        response = self.client.post(
            reverse('layer-profile-list'),
            layer_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) 