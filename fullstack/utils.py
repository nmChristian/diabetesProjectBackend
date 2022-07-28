"""
Author: Alexander
Description: Common utility functions used across the program
"""
from typing import Union, List, Optional
from bson import ObjectId
from json import JSONDecodeError
from fullstack import app, db
from bson.json_util import dumps, loads
from flask import request, abort, make_response
import jwt
import time


def jsonify(data: Union[list, dict]):
    """
    A wrapper around bson.dumps for http responses, exactly like flask.jsonify
    :param data: A bson object
    :return:
    """
    indent = None
    separators = (",", ":")

    if app.config["JSONIFY_PRETTYPRINT_REGULAR"] or app.debug:
        indent = 2
        separators = (", ", ": ")

    return app.response_class(
        dumps(data, indent=indent, separators=separators),
        mimetype=app.config["JSONIFY_MIMETYPE"]
    )


def get_json(filter: dict = None, required: Union[List[str], bool] = None) -> dict:
    """
    Parses user input and filters by chosen parameter names
    :param filter: A dictionary of (parameter, type) key-value pairs
    :param required: A list of required parameters or True if all are required.
    :return: A Json object satisfying the required conditions
    """
    try:
        json_data = loads(request.data)
    except JSONDecodeError:
        error(400, 'Invalid input')

    if filter is None:
        return json_data
    out = {}
    for key in json_data:
        if key not in filter:
            continue
        if filter[key] is not None and not isinstance(json_data[key], filter[key]):
            error(400, 'Invalid input')
        out[key] = json_data[key]

    if required is True:
        for item in filter:
            if item not in out:
                error(400, 'Missing required arguments')
    elif isinstance(required, list):
        for item in required:
            if item not in out:
                error(400, 'Missing required arguments')
    return out


def get_login() -> dict:
    """
    Gets a user object from an API key in the headers or aborts if invalid
    :return: User object
    """
    api_key = request.headers.get("api_key")
    if api_key is None:
        error(401, "Invalid API key")
    try:
        data = jwt.decode(api_key, key=app.config["SECRET_KEY"], algorithms=["HS256"])
    except (jwt.exceptions.DecodeError, jwt.exceptions.InvalidSignatureError, jwt.exceptions.InvalidAlgorithmError):
        error(400, "Invalid API key")
    else:
        user = db.users.find_one({'_id': ObjectId(data["id"])})
        if user is None:
            error(400, "Invalid user")
        return user


def create_api_key(user_id: ObjectId) -> str:
    """
    Creates an API key from a user id
    :param user_id: User ObjectId
    :return: API key string
    """
    return jwt.encode({'id': str(user_id), 'timestamp': int(time.time())}, key=app.config["SECRET_KEY"], algorithm="HS256")


def error(error_code: int, message: str):
    """
    Aborts the current thread and returns the given error code and message to the user
    :param error_code: HTTP status error code
    :param message: Message to be displayed to user
    """
    json = jsonify({'error': message})
    response = make_response(json, error_code)
    abort(response)


def check_viewable(me, id: Optional[Union[str, ObjectId]]) -> ObjectId:
    """
    Gets the id if it's viewable to the user, otherwise it aborts.
    :param me: The user object of the current user
    :param id: The id of the user to be viewed as a str or ObjectId, or None if viewing self
    :return: An ObjectId of the user to be viewed
    """
    if id is None:
        return me.get('_id')
    patient_id = ObjectId(id) if isinstance(id, str) else id

    viewable = me.get("viewable") or []
    viewable.append(me.get('_id'))
    if ObjectId(patient_id) not in viewable:
        error(403, 'Not allowed to view this user')
    return ObjectId(patient_id)


def get_objectid(id: str) -> ObjectId:
    """
    Converts a string to an ObjectId, or aborts if invalid
    :param id: 24-character hex string representing an id
    :return: The ObjectId
    """
    try:
        return ObjectId(id)
    except Exception:
        error(400, 'Invalid id')
