#!/usr/bin/env python3
"""
Author: Alexander
Description: A script for setting up the database. The primary purpose is to fill it in with dummy data, but it's
             also possible to just setup indexes, which is necessary for it to be running optimally
"""
from pymongo.errors import CollectionInvalid

try:
    from pymongo import MongoClient
except ModuleNotFoundError:
    print("Run: python -m pip install pymongo")
    exit(1)
from datetime import datetime
from time import time
import random


client = MongoClient("mongodb://localhost:27017")
db = client["fullstack"]


def setup_indexes():
    db.users.drop_indexes()
    db.users.create_index('email', unique=True, collation={'locale': 'en', 'strength': 2})

    db.diagnosis.drop_indexes()
    db.diagnosis.create_index('patient')

    db.cache.drop_indexes()
    db.cache.create_index('patient')
    db.cache.create_index('ttl')

    db.note.drop_indexes()
    db.note.create_index('patient')

    data_types = ['cgm', 'meals', 'basal', 'bolus', 'exercise']
    for data in data_types:
        try:
            db.create_collection(data, timeseries={'timeField': 'timestamp', 'granularity': 'minutes', 'metaField': 'patient'})
        except CollectionInvalid:
            pass


def add_doctor():
    patients = db.users.find({"is_doctor": {'$ne': True}}, {'_id': 1}).limit(10)

    password_hash = '$2b$12$Cy8R6vf8dLL5aX.K.Ty1Y.lHZqWeIpPiPngxTUogzHeYldUujviA2'  # password1
    doctor = db.users.insert_one({
        'email': f'Doctor@example.com',
        'password_hash': password_hash,
        'first_name': f'Dr.',
        'last_name': f'Pepper',
        'is_doctor': True,
        'viewable': [
            patient['_id'] for patient in patients
        ]
    }).inserted_id


def setup_dummy_data():
    start_time = time()
    client.drop_database("fullstack")
    setup_indexes()

    with open('data/time.csv', 'r') as f:
        format_data = "%d-%b-%Y %H:%M:%S"
        times = [datetime.strptime(t, format_data) for t in f.read().strip().split(",")]
    password_hash = '$2b$12$Cy8R6vf8dLL5aX.K.Ty1Y.lHZqWeIpPiPngxTUogzHeYldUujviA2'  # password1

    print("Adding users", time() - start_time)
    users = []
    min_age = int(datetime(2007,12,31).timestamp())

    for i in range(1000):
        age = random.randrange(0, min_age)

        users.append(db.users.insert_one({'email': f'User{i}@example.com',
                                          'password_hash': password_hash,
                                          'first_name': f'User{i}',
                                          'last_name': f'number{i}',
                                          'birthdate': datetime.fromtimestamp(age),
                                          }).inserted_id)

    last_time = datetime(year=2022,month=1,day=29)
    today = datetime.now()
    today = datetime(year=today.year, month=today.month, day=today.day)
    offset_time = today - last_time

    print("Adding CGM measurements", time() - start_time)
    cgm = []
    with open('data/measurements.csv', 'r') as f:
        l = [line.strip().split(",") for line in f]

        for j in range(len(l[0])):
            for i in range(1000):
                cgm.append({'timestamp': times[j]+offset_time, 'patient': users[i], 'value': float(l[i][j])})
    db.cgm.insert_many(cgm)
    del cgm

    print("Adding meals", time() - start_time)
    meals = []
    with open('data/meals.csv', 'r') as f:
        l = [line.strip().split(",") for line in f]
        for j in range(len(l[0])):
            for i in range(1000):
                v = float(l[i][j])
                if v != 0:
                    meals.append({'timestamp': times[j]+offset_time, 'patient': users[i], 'value': v})

    db.meals.insert_many(meals)
    del meals

    print("Adding basal", time() - start_time)
    basal = []
    with open('data/basal.csv', 'r') as f:
        l = [line.strip().split(",") for line in f]

        for j in range(len(l[0])):
            for i in range(1000):
                v = float(l[i][j])
                if v != 0:
                    basal.append({'timestamp': times[j]+offset_time, 'patient': users[i], 'value': v})

    db.basal.insert_many(basal)
    del basal

    print("Adding bolus", time() - start_time)
    bolus = []
    with open('data/bolus.csv', 'r') as f:
        l = [line.strip().split(",") for line in f]

        for j in range(len(l[0])):
            for i in range(1000):
                v = float(l[i][j])
                if v != 0:
                    bolus.append({'timestamp': times[j]+offset_time, 'patient': users[i], 'value': v})

    db.bolus.insert_many(bolus)
    del bolus

    print("Adding exercise", time() - start_time)
    exercise = []
    with open('data/exercise.csv', 'r') as f:
        l = [line.strip().split(",") for line in f]

        val_len = 0
        val = None
        for i in range(1000):
            for j in range(len(l[i])):
                v = float(l[i][j])
                if val_len > 0 and v == 0:
                    exercise.append({'timestamp': times[j - val_len]+offset_time, 'patient': users[i], 'duration': val_len * 300.0,
                                     'intensity': val / 100})
                    val = None
                    val_len = 0

                if v != 0:
                    val_len += 1
                    val = v

    db.exercise.insert_many(exercise)
    del exercise
    add_doctor()


def main():
    print("Options:")
    print("[1] Setup dummy data")
    print("[2] Setup indexes")
    print("[3] Add doctor")
    inp = int(input("> "))
    if inp == 1:
        setup_dummy_data()
    elif inp == 2:
        setup_indexes()
    elif inp == 3:
        add_doctor()
    else:
        print("Invalid")


if __name__ == '__main__':
    main()
