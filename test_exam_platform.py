import sys
from pathlib import Path
import json
import requests
from datetime import datetime
import io

sys.path.insert(0, str(Path(__file__).parent))

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:5000"


def test_homepage():
    """Test that homepage loads"""
    r = requests.get(f"{BASE_URL}/", allow_redirects=False)
    assert r.status_code in (200, 302), f"Homepage failed: {r.status_code}"
    print("[OK] Homepage loads")


def test_test_listing():
    """Test that test listing page works"""
    r = requests.get(f"{BASE_URL}/tests")
    assert r.status_code == 200
    assert b"Available Tests" in r.content or b"Mock Mathematics" in r.content
    print("[OK] Test listing page works")


def test_instructions():
    """Test that instructions page works"""
    r = requests.get(f"{BASE_URL}/test/TEST001/instructions")
    assert r.status_code == 200
    assert b"Instructions" in r.content
    print("[OK] Test instructions page works")


def test_start_test():
    """Test starting a test"""
    r = requests.post(f"{BASE_URL}/api/test/TEST001/start")
    assert r.status_code == 200
    data = r.json()
    assert "attempt_id" in data
    assert "redirect_url" in data
    print(f"[OK] Test start works (Attempt ID: {data['attempt_id'][:8]}...)")
    return data["attempt_id"]


def test_get_questions(attempt_id):
    """Test loading questions"""
    r = requests.get(f"{BASE_URL}/api/attempt/{attempt_id}/questions")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    assert data[0]["question_type"] in ("mcq", "subjective")
    print(f"[OK] Questions loaded ({len(data)} questions)")
    return data


def test_save_mcq_response(attempt_id):
    """Test saving MCQ response"""
    r = requests.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q001", "selected_answer": "B"}
    )
    assert r.status_code == 200
    print("[OK] MCQ response saved")


def test_save_subjective_response(attempt_id):
    """Test saving subjective response"""
    r = requests.post(
        f"{BASE_URL}/api/attempt/{attempt_id}/response",
        json={"question_id": "Q005", "selected_answer": "A"}
    )
    assert r.status_code == 200
    print("[OK] Subjective response saved")


def test_submission_preview(attempt_id):
    """Test submission preview"""
    r = requests.get(f"{BASE_URL}/api/attempt/{attempt_id}/submit-preview")
    assert r.status_code == 200
    data = r.json()
    assert "total_questions" in data
    assert "answered" in data
    print(f"[OK] Submission preview works (Answered: {data['answered']}/{data['total_questions']})")


def test_submit_attempt(attempt_id):
    """Test submitting attempt"""
    r = requests.post(f"{BASE_URL}/api/attempt/{attempt_id}/submit")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "submitted"
    print("[OK] Test submitted successfully")


def test_confirmation_page(attempt_id):
    """Test confirmation page"""
    r = requests.get(f"{BASE_URL}/submission/{attempt_id}")
    assert r.status_code == 200
    assert b"submitted" in r.content.lower()
    print("[OK] Confirmation page works")


def run_all_tests():
    """Run all tests"""
    print("\n=== EXAM PLATFORM TEST SUITE ===\n")
    
    try:
        test_homepage()
        test_test_listing()
        test_instructions()
        
        # Test the full exam flow
        attempt_id = test_start_test()
        
        questions = test_get_questions(attempt_id)
        
        test_save_mcq_response(attempt_id)
        test_save_subjective_response(attempt_id)
        
        test_submission_preview(attempt_id)
        
        test_submit_attempt(attempt_id)
        
        test_confirmation_page(attempt_id)
        
        print("\n=== ALL TESTS PASSED ===\n")
        return True
    
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
