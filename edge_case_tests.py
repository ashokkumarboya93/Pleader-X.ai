#!/usr/bin/env python3
"""
Edge case testing for Pleader AI Backend
Tests authentication edge cases and error handling
"""

import requests
import json

BASE_URL = "https://public-pleader.preview.emergentagent.com/api"

def test_auth_edge_cases():
    """Test authentication edge cases"""
    session = requests.Session()
    
    print("🔍 Testing Authentication Edge Cases")
    print("-" * 40)
    
    # Test invalid login credentials
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": "nonexistent@test.com", "password": "wrongpass"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 401:
        print("✅ Invalid login credentials properly rejected")
    else:
        print(f"❌ Invalid login should return 401, got {response.status_code}")
    
    # Test accessing protected endpoint without token
    response = session.get(f"{BASE_URL}/auth/me")
    
    if response.status_code == 401:
        print("✅ Protected endpoint properly requires authentication")
    else:
        print(f"❌ Protected endpoint should return 401, got {response.status_code}")
    
    # Test with invalid token
    session.headers.update({"Authorization": "Bearer invalid_token_here"})
    response = session.get(f"{BASE_URL}/auth/me")
    
    if response.status_code == 401:
        print("✅ Invalid token properly rejected")
    else:
        print(f"❌ Invalid token should return 401, got {response.status_code}")

def test_input_validation():
    """Test input validation"""
    session = requests.Session()
    
    print("\n🔍 Testing Input Validation")
    print("-" * 40)
    
    # Test signup with invalid email
    response = session.post(
        f"{BASE_URL}/auth/signup",
        json={"name": "Test", "email": "invalid-email", "password": "TestPass123"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 422:  # Validation error
        print("✅ Invalid email format properly rejected")
    else:
        print(f"❌ Invalid email should return 422, got {response.status_code}")
    
    # Test signup with short password
    response = session.post(
        f"{BASE_URL}/auth/signup",
        json={"name": "Test", "email": "test@example.com", "password": "123"},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 422:  # Validation error
        print("✅ Short password properly rejected")
    else:
        print(f"❌ Short password should return 422, got {response.status_code}")

def test_rate_limiting():
    """Test rate limiting (basic check)"""
    session = requests.Session()
    
    print("\n🔍 Testing Rate Limiting")
    print("-" * 40)
    
    # Make multiple rapid requests to signup endpoint
    failed_requests = 0
    for i in range(10):
        response = session.post(
            f"{BASE_URL}/auth/signup",
            json={"name": f"Test{i}", "email": f"test{i}@spam.com", "password": "TestPass123"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 429:  # Rate limited
            failed_requests += 1
    
    if failed_requests > 0:
        print(f"✅ Rate limiting active - {failed_requests} requests rate limited")
    else:
        print("ℹ️  Rate limiting not triggered in this test")

if __name__ == "__main__":
    test_auth_edge_cases()
    test_input_validation()
    test_rate_limiting()
    print("\n✅ Edge case testing completed")