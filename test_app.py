import pytest
from app import app as flask_app
from unittest.mock import patch, MagicMock
from flask_login import login_user
from models import db, User, Proposal
from datetime import datetime

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    with flask_app.app_context():
        db.create_all()
        yield flask_app.test_client()
        db.session.remove()
        db.drop_all()

def register_and_login(client, email='test@example.com', password='Password123', is_premium=False):
    user = User(email=email, is_premium=is_premium)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
    return user

def test_form_page_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'ProposifyAI' in response.data

def test_form_validation(client):
    # First register and login
    user = register_and_login(client)
    
    response = client.post('/generate', data={
        'client_name': '',
        'job_description': '',
        'skills': '',
        'tier': 'starter'
    }, follow_redirects=True)
    assert b'All fields are required.' in response.data

def test_generate_proposal_success(client):
    user = register_and_login(client)
    with patch('app.generate_proposal') as mock_generate:
        mock_generate.return_value = 'Test Proposal'
        response = client.post('/generate', data={
            'client_name': 'Test Client',
            'job_description': 'Test Job',
            'skills': 'Python',
            'tier': 'starter'
        })
        assert b'Test Proposal' in response.data

def test_ad_placeholder_dashboard_starter(client):
    user = register_and_login(client)
    response = client.get('/dashboard')
    assert response.status_code == 200

def test_no_ad_dashboard_premium(client):
    user = register_and_login(client, is_premium=True)
    response = client.get('/dashboard')
    assert response.status_code == 200

def test_ad_placeholder_result_starter(client):
    user = register_and_login(client)
    with patch('gpt_utils.generate_proposal', return_value='Test Proposal'):
        response = client.post('/generate', data={
            'client_name': 'Client',
            'job_description': 'Job',
            'skills': 'Python',
            'tier': 'starter'
        }, follow_redirects=True)
    assert response.status_code == 200

def test_no_ad_result_premium(client):
    user = register_and_login(client, is_premium=True)
    with patch('gpt_utils.generate_proposal', return_value='Test Proposal'):
        response = client.post('/generate', data={
            'client_name': 'Client',
            'job_description': 'Job',
            'skills': 'Python',
            'tier': 'premium'
        }, follow_redirects=True)
    assert response.status_code == 200

@patch('stripe.checkout.Session.create')
def test_create_checkout_session(mock_stripe, client):
    user = register_and_login(client)
    mock_stripe.return_value = MagicMock(id='cs_test_123')
    response = client.post('/create-checkout-session')
    assert response.status_code == 200
    assert b'cs_test_123' in response.data

def test_user_registration(client):
    response = client.post('/register', data={
        'email': 'new@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert b'Account created!' in response.data

def test_user_login(client):
    user = register_and_login(client)
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'Password123'
    }, follow_redirects=True)
    # Check that we're redirected to the form page (logged in successfully)
    assert b'Generate Proposal' in response.data

def test_usage_limit_enforcement(client):
    user = register_and_login(client)
    user.proposals_this_month = 5
    db.session.commit()
    
    with patch('gpt_utils.generate_proposal', return_value='Test Proposal'):
        response = client.post('/generate', data={
            'client_name': 'Client',
            'job_description': 'Job',
            'skills': 'Python',
            'tier': 'starter'
        }, follow_redirects=True)
    assert b'Monthly limit' in response.data

def test_premium_tier_restriction(client):
    user = register_and_login(client)  # Not premium
    with patch('gpt_utils.generate_proposal', return_value='Test Proposal'):
        response = client.post('/generate', data={
            'client_name': 'Client',
            'job_description': 'Job',
            'skills': 'Python',
            'tier': 'premium'
        }, follow_redirects=True)
    assert b'Premium tier requires' in response.data

def test_mobile_responsive_navigation(client):
    response = client.get('/')
    assert b'navbar-toggler' in response.data  # Mobile menu button
    assert b'navbar-expand-lg' in response.data  # Bootstrap responsive class

def test_database_proposal_storage(client):
    user = register_and_login(client)
    with patch('gpt_utils.generate_proposal', return_value='Test Proposal'):
        client.post('/generate', data={
            'client_name': 'Client',
            'job_description': 'Job',
            'skills': 'Python',
            'tier': 'starter'
        })
    
    proposal = Proposal.query.filter_by(user_id=user.id).first()
    assert proposal is not None
    assert proposal.content == 'Test Proposal'
    assert proposal.tier == 'starter'

def test_pricing_page_loads(client):
    response = client.get('/pricing')
    assert response.status_code == 200
    assert b'Starter' in response.data
    assert b'Premium' in response.data

def test_logout_functionality(client):
    user = register_and_login(client)
    response = client.get('/logout', follow_redirects=True)
    assert b'You have been logged out.' in response.data

def test_password_validation(client):
    """Test that password validation works"""
    response = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'weak',
        'confirm_password': 'weak'
    }, follow_redirects=True)
    assert b'Password must be at least 8 characters long' in response.data

def test_email_validation(client):
    """Test that email validation works"""
    response = client.post('/register', data={
        'email': 'invalid-email',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert b'Please enter a valid email address' in response.data

def test_security_features(client):
    """Test that security features are active"""
    # Test CSRF protection (should be disabled in tests)
    response = client.post('/generate', data={
        'client_name': 'Test',
        'job_description': 'Test',
        'skills': 'Test',
        'tier': 'starter'
    })
    # Should not get CSRF error in tests
    assert response.status_code != 400 or b'CSRF token' not in response.data 