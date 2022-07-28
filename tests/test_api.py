import time

import pytest
from flask.testing import FlaskClient
import os
from bson import ObjectId


os.environ["TESTING"] = "TRUE"
os.environ["MONGO_DB_NAME"] = "test"
from fullstack import app, db, mongo_client


@pytest.fixture
def client() -> FlaskClient:
    mongo_client.drop_database(os.getenv("MONGO_DB_NAME"))
    db.users.create_index('email', unique=True)
    client = app.test_client()
    yield client


def get_uid(client: FlaskClient, api_key):
    out = client.get("/api/v1/user", headers={'api_key': api_key})
    assert out.status_code == 200
    return out.json['self']['_id']['$oid']


def get_doctor(client: FlaskClient):
    patient = test_login(client, 'patient@example.com')
    doctor = test_login(client, 'doctor@example.com')

    db.users.update_one({'_id': ObjectId(get_uid(client, doctor))}, {'$set': {'is_doctor': True, 'viewable': [ObjectId(get_uid(client, patient))]}})
    return doctor, patient


def test_signup(client: FlaskClient, email='test@example.com'):
    out = client.post("/api/v1/user/", json={'email': email, 'first_name': 'test', 'last_name': 'test',
                                             'birthdate': '2000-01-01',
                                             'password': 'hello', 'password_check': 'hello'})
    assert out.status_code == 200


def test_fail_signup(client: FlaskClient):
    out = client.post("/api/v1/user/", json={'email': 'test@example.com', 'first_name': 'test', 'last_name': 'test',
                                             'birthdate': '2000-01-01',
                                             'password': 'hello', 'password_check': 'other'})
    assert out.status_code == 400


def test_fail_signup2(client: FlaskClient):
    out = client.post("/api/v1/user/", json={'email': 'test@example.com',
                                             'birthdate': '2000-01-01',
                                             'password': 'hello', 'password_check': 'hello'})
    assert out.status_code == 400


def test_fail_signup3(client: FlaskClient):
    test_signup(client, 'test@example.com')
    out = client.post("/api/v1/user/", json={'email': 'test@example.com', 'first_name': 'test', 'last_name': 'test',
                                             'birthdate': '2000-01-01',
                                             'password': 'hello', 'password_check': 'hello'})
    assert out.status_code == 400


def test_login(client: FlaskClient, email='test@example.com'):
    test_signup(client, email)
    out = client.post('/api/v1/user/login', json={'email': email, 'password': 'hello'})
    assert out.status_code == 200
    assert "api_key" in out.json
    return out.json["api_key"]


def test_post_cgm(client: FlaskClient):
    api_key = test_login(client)
    out = client.post('/api/v1/data/', json={'type': 'cgm', 'timestamp': int(time.time()) - 300, 'value': 0.5}, headers={'api_key': api_key})
    assert out.status_code == 200
    return api_key


def test_get_cgm(client: FlaskClient):
    api_key = test_post_cgm(client)
    out = client.post('/api/v1/data/get', json={'show': ['cgm'], 'ndays': 1}, headers={'api_key': api_key})
    assert out.status_code == 200
    assert 'cgm' in out.json
    assert len(out.json['cgm']) == 1


def test_note(client: FlaskClient):
    api_key = test_login(client)
    out = client.post("/api/v1/note", json={'text': 'foo'}, headers={'api_key': api_key})
    assert out.status_code == 200

    out = client.get("/api/v1/note", headers={'api_key': api_key})
    assert out.status_code == 200
    assert out.json[0]['text'] == 'foo'
    note_id = out.json[0]['_id']['$oid']

    out = client.put(f"/api/v1/note/{note_id}", json={'text': 'bar'}, headers={'api_key': api_key})
    assert out.status_code == 200

    out = client.get("/api/v1/note", headers={'api_key': api_key})
    assert out.status_code == 200
    assert out.json[0]['text'] == 'bar'

    out = client.delete(f"/api/v1/note/{note_id}", headers={'api_key': api_key})
    assert out.status_code == 200

    out = client.get("/api/v1/note", headers={'api_key': api_key})
    assert out.status_code == 200
    assert len(out.json) == 0


def test_diagnosis(client: FlaskClient):
    doctor, patient = get_doctor(client)
    patient_id = get_uid(client, patient)
    out = client.post(f"/api/v1/diagnosis/{patient_id}", json={'name': 'diagnosis1', 'medicine': ['medicine1']}, headers={'api_key': doctor})
    assert out.status_code == 200

    out = client.get(f"/api/v1/diagnosis", headers={'api_key': patient})
    assert out.json[0]['name'] == 'diagnosis1'
    assert out.json[0]['medicine'] == ['medicine1']
    diag_id = out.json[0]['_id']['$oid']

    out = client.put(f"/api/v1/diagnosis/{diag_id}", json={'medicine': ['medicine1', 'medicine2']}, headers={'api_key': doctor})
    assert out.status_code == 200

    out = client.get(f"/api/v1/diagnosis", headers={'api_key': patient})
    assert out.json[0]['name'] == 'diagnosis1'
    assert out.json[0]['medicine'] == ['medicine1', 'medicine2']

    out = client.delete(f"/api/v1/diagnosis/{diag_id}", headers={'api_key': doctor})
    assert out.status_code == 200

    out = client.get(f"/api/v1/diagnosis", headers={'api_key': patient})
    assert len(out.json) == 0
