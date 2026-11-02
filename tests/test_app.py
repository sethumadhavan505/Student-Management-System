import pytest
from app import create_app

@pytest.fixture()
def client(tmp_path):
    app=create_app({"TESTING":True,"DATABASE":str(tmp_path/"test.sqlite")})
    with app.test_client() as client: yield client

def student(**overrides):
    data={"name":"Asha Kumar","roll_number":"IT001","department":"Information Technology","email":"asha@example.com"}
    data.update(overrides); return data

def test_home_page(client):
    response=client.get("/")
    assert response.status_code==200
    assert b"Student Management System" in response.data

def test_create_and_list(client):
    response=client.post("/api/students",json=student())
    assert response.status_code==201
    assert len(client.get("/api/students").json)==1

def test_invalid_email(client):
    response=client.post("/api/students",json=student(email="bad"))
    assert response.status_code==400

def test_duplicate_rejected(client):
    client.post("/api/students",json=student())
    response=client.post("/api/students",json=student(email="other@example.com"))
    assert response.status_code==400

def test_update_delete(client):
    sid=client.post("/api/students",json=student()).json["id"]
    assert client.put(f"/api/students/{sid}",json=student(name="Asha Updated")).status_code==200
    assert client.delete(f"/api/students/{sid}").status_code==200
