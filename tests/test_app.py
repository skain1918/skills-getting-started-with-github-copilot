"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities before each test"""
    from app import activities
    
    # Store original state
    original_state = {
        k: {"participants": v["participants"].copy(), **{kk: vv for kk, vv in v.items() if kk != "participants"}}
        for k, v in activities.items()
    }
    
    yield
    
    # Restore original state
    for activity_name, activity_data in activities.items():
        activity_data["participants"] = original_state[activity_name]["participants"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Basketball Team" in data
        assert "Tennis Club" in data
        assert "Debate Team" in data
    
    def test_get_activities_has_required_fields(self, client):
        """Test that activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
    
    def test_get_activities_participants_is_list(self, client):
        """Test that participants is a list"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert isinstance(activity_data["participants"], list)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_valid_student(self, client, reset_activities):
        """Test successful signup for a student"""
        response = client.post(
            "/activities/Basketball Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        # Get initial count
        response_before = client.get("/activities")
        before_count = len(response_before.json()["Basketball Team"]["participants"])
        
        # Signup new student
        client.post("/activities/Basketball Team/signup?email=newstudent@mergington.edu")
        
        # Get updated count
        response_after = client.get("/activities")
        after_count = len(response_after.json()["Basketball Team"]["participants"])
        
        assert after_count == before_count + 1
        assert "newstudent@mergington.edu" in response_after.json()["Basketball Team"]["participants"]
    
    def test_signup_invalid_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/NonExistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_student(self, client, reset_activities):
        """Test that a student cannot sign up twice for the same activity"""
        # First signup
        client.post("/activities/Basketball Team/signup?email=duplicate@mergington.edu")
        
        # Attempt duplicate signup
        response = client.post(
            "/activities/Basketball Team/signup?email=duplicate@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_existing_participant(self, client):
        """Test that an existing participant cannot sign up again"""
        response = client.post(
            "/activities/Basketball Team/signup?email=james@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_valid_participant(self, client, reset_activities):
        """Test successful unregistration of a participant"""
        # First add a participant
        client.post("/activities/Basketball Team/signup?email=teststudent@mergington.edu")
        
        # Then unregister them
        response = client.delete(
            "/activities/Basketball Team/unregister?email=teststudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "teststudent@mergington.edu" in data["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        # Add a participant
        client.post("/activities/Basketball Team/signup?email=teststudent@mergington.edu")
        
        # Get count before unregister
        response_before = client.get("/activities")
        before_count = len(response_before.json()["Basketball Team"]["participants"])
        
        # Unregister
        client.delete(
            "/activities/Basketball Team/unregister?email=teststudent@mergington.edu"
        )
        
        # Get count after unregister
        response_after = client.get("/activities")
        after_count = len(response_after.json()["Basketball Team"]["participants"])
        
        assert after_count == before_count - 1
        assert "teststudent@mergington.edu" not in response_after.json()["Basketball Team"]["participants"]
    
    def test_unregister_invalid_activity(self, client):
        """Test unregister for non-existent activity"""
        response = client.delete(
            "/activities/NonExistent Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_registered_participant(self, client):
        """Test that unregistering a non-registered participant fails"""
        response = client.delete(
            "/activities/Basketball Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        response = client.delete(
            "/activities/Basketball Team/unregister?email=james@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify they're removed
        response_after = client.get("/activities")
        assert "james@mergington.edu" not in response_after.json()["Basketball Team"]["participants"]


class TestRoot:
    """Tests for GET / endpoint"""
    
    def test_root_redirects(self, client):
        """Test that root redirects to static page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestEdgeCases:
    """Tests for edge cases and integration scenarios"""
    
    def test_signup_and_unregister_cycle(self, client, reset_activities):
        """Test the complete signup and unregister cycle"""
        email = "cycle@mergington.edu"
        
        # Sign up
        response1 = client.post(
            f"/activities/Tennis Club/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Verify signed up
        response2 = client.get("/activities")
        assert email in response2.json()["Tennis Club"]["participants"]
        
        # Unregister
        response3 = client.delete(
            f"/activities/Tennis Club/unregister?email={email}"
        )
        assert response3.status_code == 200
        
        # Verify unregistered
        response4 = client.get("/activities")
        assert email not in response4.json()["Tennis Club"]["participants"]
    
    def test_multiple_activities_signup(self, client, reset_activities):
        """Test that a student can sign up for multiple activities"""
        email = "multi@mergington.edu"
        
        # Sign up for multiple activities
        response1 = client.post(f"/activities/Basketball Team/signup?email={email}")
        assert response1.status_code == 200
        
        response2 = client.post(f"/activities/Tennis Club/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify in both activities
        response = client.get("/activities")
        assert email in response.json()["Basketball Team"]["participants"]
        assert email in response.json()["Tennis Club"]["participants"]
