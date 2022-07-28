"""
Author: Alexander
Description: Note endpoint, for operations on notes
"""
from datetime import datetime
from typing import Optional

from fullstack import db

from flask_classy import FlaskView, route
from fullstack.utils import jsonify, get_json, get_login, error, check_viewable, get_objectid


class NoteView(FlaskView):

    @route('/', methods=["GET"])
    @route('/<string:id_str>/', methods=["GET"])
    def get_note(self, id_str: Optional[str] = None):
        me = get_login()
        patient_id = check_viewable(me, id_str)

        if me.get("is_doctor"):
            return jsonify(db.note.find({'patient': patient_id}, {'text': 1, 'timestamp': 1, 'writer': 1, 'private': 1}))
        else:
            return jsonify(db.note.find({'patient': patient_id, 'private': {'$ne': True}}, {'text': 1, 'timestamp': 1, 'writer': 1}))

    @route('/', methods=["POST"])
    @route("/<string:id_str>/", methods=["POST"])
    def post_note(self, id_str: Optional[str] = None):
        me = get_login()
        patient_id = check_viewable(me, id_str)
        inp = get_json({'text': str, 'private': bool}, required=['text'])
        db.note.insert_one({'text': inp['text'], 'private': inp.get('private') or False, 'timestamp': datetime.now(), 'patient': patient_id, 'writer': me.get('_id')})
        return {'message': 'Added note'}

    @route("/<string:note_id>/", methods=["PUT"])
    def put_note(self, note_id: str):
        me = get_login()
        note = db.note.find_one({'_id': get_objectid(note_id)})
        if note is None:
            error(404, 'Invalid note')
        check_viewable(me, note['patient'])
        if not me.get('is_doctor') and me['_id'] != note["writer"]:
            error(403, 'You are not allowed to update this note')

        inp = get_json({'text': str, 'private': bool})
        if 'private' in inp and not me.get('is_doctor'):
            del inp['private']
        db.note.update_one({'_id': get_objectid(note_id)}, {'$set': inp})
        return {'message': 'Updated note'}

    @route('/<string:note_id>/', methods=["DELETE"])
    def delete_note(self, note_id: str):
        me = get_login()
        note = db.note.find_one({'_id': get_objectid(note_id)})
        if note is None:
            error(404, 'Invalid note')
        check_viewable(me, note['patient'])
        if not me.get('is_doctor') and me['_id'] != note["writer"]:
            error(403, 'You are not allowed to update this note')

        db.note.delete_one({'_id': get_objectid(note_id)})
        return {'message': 'Deleted note'}
