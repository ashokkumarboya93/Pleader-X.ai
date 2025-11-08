import pytest
from fastapi.testclient import TestClient
from server import app
import json

client = TestClient(app)

# Test data
test_user = {
    "name": "Test User",
    "email": f"test_{id(app)}@test.com",
    "password": "TestPass123"
}

test_token = None

# ==================== HEALTH & SYSTEM TESTS ====================

def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "git_commit" in data
    assert "services" in data

# ==================== AUTHENTICATION TESTS ====================

def test_signup():
    """Test user signup"""
    response = client.post("/api/auth/signup", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "user" in data
    assert data["user"]["email"] == test_user["email"]
    
    # Store token for other tests
    global test_token
    test_token = data["token"]

def test_signup_duplicate_email():
    """Test signup with existing email"""
    response = client.post("/api/auth/signup", json=test_user)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_login():
    """Test user login"""
    response = client.post("/api/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"]
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == test_user["email"]

def test_login_invalid_credentials():
    """Test login with invalid password"""
    response = client.post("/api/auth/login", json={
        "email": test_user["email"],
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_get_me():
    """Test get current user"""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]

def test_get_me_unauthorized():
    """Test get current user without token"""
    response = client.get("/api/auth/me")
    assert response.status_code == 403  # HTTPBearer returns 403

# ==================== CHAT TESTS ====================

def test_send_message_new_chat():
    """Test sending message to new chat"""
    response = client.post(
        "/api/chat/send",
        json={"message": "What is Section 420 IPC?", "mode": "concise"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "chat_id" in data
    assert "message" in data
    assert data["message"]["sender"] == "ai"

def test_get_chat_history():
    """Test getting chat history"""
    response = client.get(
        "/api/chat/history",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "chats" in data
    assert len(data["chats"]) > 0

def test_send_message_validation():
    """Test message validation"""
    response = client.post(
        "/api/chat/send",
        json={"message": ""},  # Empty message
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 422  # Validation error

# ==================== RAG TESTS ====================

def test_rag_stats():
    """Test RAG statistics endpoint"""
    response = client.get(
        "/api/rag/stats",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data or "total_chunks" in data

def test_rag_query_validation():
    """Test RAG query validation"""
    response = client.post(
        "/api/rag/query",
        json={"query": "", "top_k": 5},  # Empty query
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 422  # Validation error

def test_rag_query_top_k_limit():
    """Test RAG query top_k limits"""
    response = client.post(
        "/api/rag/query",
        json={"query": "test", "top_k": 100},  # Exceeds max
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 422

# ==================== DOCUMENT TESTS ====================

def test_get_documents():
    """Test getting document list"""
    response = client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data

def test_upload_invalid_file_type():
    """Test uploading unsupported file type"""
    files = {"file": ("test.exe", b"fake content", "application/exe")}
    response = client.post(
        "/api/documents/analyze",
        files=files,
        data={"document_type": "legal_document"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

# ==================== RATE LIMITING TESTS ====================

def test_rate_limiting():
    """Test rate limiting on health endpoint"""
    # Make many requests to trigger rate limit
    responses = []
    for i in range(65):  # Health endpoint limit is 60/minute
        response = client.get("/health")
        responses.append(response.status_code)
    
    # At least one should be rate limited
    assert 429 in responses

# ==================== INPUT SANITIZATION TESTS ====================

def test_signup_name_sanitization():
    """Test name sanitization in signup"""
    response = client.post("/api/auth/signup", json={
        "name": "A",  # Too short
        "email": f"test_short_{id(app)}@test.com",
        "password": "TestPass123"
    })
    assert response.status_code == 422

def test_message_length_limit():
    """Test message length validation"""
    long_message = "A" * 10001  # Exceeds limit
    response = client.post(
        "/api/chat/send",
        json={"message": long_message},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    # Should either reject or truncate
    assert response.status_code in [200, 422]

# ==================== EXPORT TESTS ====================

def test_export_chat_invalid_format():
    """Test export with invalid format"""
    response = client.get(
        "/api/chat/fake-id/export/xml",  # Invalid format
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]

def test_export_nonexistent_chat():
    """Test export of non-existent chat"""
    response = client.get(
        "/api/chat/nonexistent-id/export/pdf",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 404

# ==================== PREFERENCES TESTS ====================

def test_update_preferences():
    """Test updating user preferences"""
    new_prefs = {
        "theme": "dark",
        "language": "hi",
        "notifications": False
    }
    response = client.put(
        "/api/user/preferences",
        json=new_prefs,
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    
    # Verify preferences were updated
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert me_response.json()["preferences"]["theme"] == "dark"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
