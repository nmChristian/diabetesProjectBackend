"""
Author: Alexander
Description: User endpoint, for operations on users
"""
import datetime
import os
import random
import re
import string

from bson.errors import InvalidId
from pymongo.collation import Collation
from pymongo.errors import DuplicateKeyError

from fullstack import db, DEFAULT_GLYCEMIC_RANGES, DEFAULT_GLYCEMIC_TARGETS

from flask import request
from flask_classy import FlaskView, route
from fullstack.utils import jsonify, get_json, create_api_key, get_login, error, check_viewable, get_objectid
import bcrypt


def calculate_age(born):
    today = datetime.date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class UserView(FlaskView):
    @route('/', methods=["GET"])
    def get_users(self):
        me = get_login()
        viewable = me.get("viewable") or []
        viewable.append(me.get('_id'))
        users = db.users.find({'_id': {'$in': viewable}, 'is_doctor': {'$ne': True}}, {'first_name': 1, 'last_name': 1,
                                                                                       'birthdate': 1, 'email': 1,
                                                                                       'glycemic_ranges': 1, 'glycemic_targets': 1,
                                                                                       'extra_data': 1,
                                                                                       'profile_picture': 1, '_id': 1})
        viewable_list = []
        for user in users:
            if 'birthdate' in user:
                user['age'] = calculate_age(user['birthdate'])
                del user['birthdate']
            if 'glycemic_ranges' not in user:
                user['glycemic_ranges'] = DEFAULT_GLYCEMIC_RANGES
            if 'glycemic_targets' not in user:
                user['glycemic_targets'] = DEFAULT_GLYCEMIC_TARGETS
            if user.get('_id') == me.get('_id'):
                viewable_list.insert(0, user)
            else:
                viewable_list.append(user)
        myself = db.users.find_one({'_id': me.get('_id')}, {'first_name': 1, 'last_name': 1, 'birthdate': 1, 'email': 1, 'is_doctor': 1, 'profile_picture': 1, '_id': 1})
        if 'birthdate' in myself:
            myself['age'] = calculate_age(myself['birthdate'])
            del myself['birthdate']
        return jsonify({'self': myself, 'viewable': viewable_list})

    @route('/<string:id_str>', methods=["GET"])
    def get_user(self, id_str: str):
        me = get_login()
        user_id = check_viewable(me, id_str)

        try:
            user = db.users.find_one({'_id': user_id}, {'first_name': 1, 'last_name': 1, 'birthdate': 1, 'email': 1,
                                                        'glycemic_ranges': 1, 'glycemic_targets': 1, 'extra_data': 1,
                                                        'is_doctor': 1, 'profile_picture': 1, '_id': 0})
        except InvalidId:
            error(400, 'Invalid id')
        else:
            if 'birthdate' in user:
                user['age'] = calculate_age(user['birthdate'])
                del user['birthdate']

            if user is None:
                error(404, 'User not found')

            return jsonify(user)

    @route('/', methods=["POST"])
    def post_user(self):
        data = get_json({'email': str, 'first_name': str, 'last_name': str, 'password': str, 'password_check': str, 'birthdate': str}, required=True)
        if data['password'] != data['password_check']:
            error(400, 'Password does not match check')
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode()

        try:
            data['birthdate'] = datetime.datetime.strptime(data['birthdate'], "%Y-%m-%d")
        except ValueError:
            error(400, 'Invalid birthdate')

        new_user = {
            'email': data['email'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'birthdate': data['birthdate'],
            'password_hash': password_hash
        }
        try:
            db.users.insert_one(new_user)
        except DuplicateKeyError:
            error(400, 'Email already in use')
        return jsonify({'message': 'Added user'})

    @route('/', methods=["PUT"])
    def put_self(self):
        me = get_login()
        return self.put_user(str(me.get("_id")))

    @route('/image', methods=["PUT"])
    def upload_profile_picture(self):
        me = get_login()
        if 'image' not in request.files:
            error(400, 'No image chosen')
        file = request.files['image']
        if file.filename == '':
            error(400, 'No image chosen')
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if file and ext in {'png', 'jpg', 'jpeg'}:
            filename = "".join(random.choice(string.hexdigits) for _ in range(16)) + "." + ext
            file.save(os.path.join('fullstack/static/images', filename))
            db.users.update_one({'_id': me.get('_id')}, {'$set': {'profile_picture': f'/static/images/{filename}'}})
            return jsonify({'message': 'Uploaded profile picture'})
        else:
            error(400, 'Invalid profile picture')

    @route('/<string:id>', methods=["PUT"])
    def put_user(self, id: str):
        me = get_login()
        # TODO: Doctors may have access to update some data here
        if me.get("_id") != get_objectid(id):
            error(403, 'Can only change your own data')
        data = get_json({'first_name': str, 'last_name': str, 'email': str, 'birthdate': str})

        # Validate fields
        if 'first_name' in data:
            if not data['first_name']:
                del data['first_name']
        if 'last_name' in data:
            if not data['last_name']:
                del data['last_name']
        if 'email' in data:
            if not data['email']:
                del data['email']
            else:
                if not re.fullmatch(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", data['email']):
                    error(400, 'Invalid email')
        if 'birthdate' in data:
            if not data['birthdate']:
                del data['birthdate']
            else:
                try:
                    data['birthdate'] = datetime.datetime.strptime(data['birthdate'], "%Y-%m-%d")
                except ValueError:
                    error(400, 'Invalid birthdate')
        try:
            db.users.update_one({'_id': get_objectid(id)}, {'$set': data})
        except DuplicateKeyError:
            error(400, 'Email already in use')
        except InvalidId:
            error(400, 'Invalid id')
        return jsonify({'message': 'Updated user'})

    @route('/login', methods=["POST"])
    def login_user(self):
        data = get_json({'email': str, 'password': str}, required=True)
        user = db.users.find_one({'email': data["email"]}, collation=Collation("en", strength=2))

        if user is None:
            error(401, 'Invalid login')

        if bcrypt.checkpw(data['password'].encode('utf-8'), user["password_hash"].encode()):
            api_key = create_api_key(user["_id"])
            return jsonify({"api_key": api_key})
        else:
            error(401, 'Invalid login')

    @route('/glycemic/<string:id_str>', methods=["PUT"])
    def put_glycemic_parameters(self, id_str):
        me = get_login()
        if not me.get("is_doctor"):
            error(403, 'Only doctors can update glycemic parameters')
        patient_id = check_viewable(me, id_str)
        data = get_json({'glycemic_ranges': list, 'glycemic_targets': list})
        if 'glycemic_ranges' in data:
            if len(data['glycemic_ranges']) != 4:
                error(400, 'Invalid glycemic ranges')
            last = 0
            for i in data['glycemic_ranges']:
                if isinstance(i, int):
                    i = float(i)
                if not isinstance(i, float) or i <= last:
                    error(400, 'Invalid glycemic ranges')
                last = i
        if 'glycemic_targets' in data:
            if len(data['glycemic_targets']) != 5:
                error(400, 'Invalid glycemic targets')
            for i in data['glycemic_targets']:
                if not isinstance(i, float) or i < 0 or i > 1:
                    error(400, 'Invalid glycemic targets')

        db.users.update_one({'_id': patient_id}, {'$set': data})
        return jsonify({'message': 'Updated glycemic parameters'})
