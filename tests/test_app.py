import pytest
from app import create_app

@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    with app.test_client() as client:
        yield client

def student(**overrides):
    data = {"name": "Asha Kumar", "roll_number": "IT001", "department": "Information Technology", "email": "asha@example.com"}
    data.update(overrides)
    return data

def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Student Management System" in response.data

def test_create_and_list(client):
    response = client.post("/api/students", json=student())
    assert response.status_code == 201
    assert len(client.get("/api/students").json) == 1

def test_invalid_email_rejected(client):
    response = client.post("/api/students", json=student(email="invalid"))
    assert response.status_code == 400
    assert "valid email" in response.json["error"]

def test_duplicate_student_rejected(client):
    client.post("/api/students", json=student())
    response = client.post("/api/students", json=student(email="other@example.com"))
    assert response.status_code == 400

def test_update_and_delete(client):
    created = client.post("/api/students", json=student())
    sid = created.json["id"]
    updated = client.put(f"/api/students/{sid}", json=student(name="Asha Updated"))
    assert updated.status_code == 200
    assert updated.json["name"] == "Asha Updated"
    assert client.delete(f"/api/students/{sid}").status_code == 200
