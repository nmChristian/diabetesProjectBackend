"""
Author: Alexander
Description: Diagnosis endpoint, for operations on diagnoses
"""
from typing import Optional

from fullstack import db

from flask_classy import FlaskView, route
from fullstack.utils import jsonify, get_json, get_login, error, check_viewable, get_objectid


class DiagnosisView(FlaskView):

    @route('/', methods=["GET"])
    @route('/<string:id_str>/', methods=["GET"])
    def get_diagnosis(self, id_str: Optional[str] = None):
        me = get_login()
        patient_id = check_viewable(me, id_str)

        return jsonify(db.diagnosis.find({'patient': patient_id}, {'name': 1, 'medicine': 1}))

    @route("/<string:id_str>/", methods=["POST"])
    def post_diagnosis(self, id_str: str):
        me = get_login()
        if not me.get("is_doctor"):
            error(403, 'Only doctors can update diagnoses')
        patient_id = check_viewable(me, id_str)

        inp = get_json({'name': str, 'medicine': list}, required=True)
        for med in inp['medicine']:
            if not isinstance(med, str):
                error(400, 'Invalid input')

        db.diagnosis.insert_one({'name': inp['name'], 'medicine': inp['medicine'], 'patient': patient_id})
        return {'message': 'Added diagnosis'}

    @route("/<string:diagnosis_id>/", methods=["PUT"])
    def put_diagnosis(self, diagnosis_id: str):
        me = get_login()
        if not me.get("is_doctor"):
            error(403, 'Only doctors can update diagnoses')
        diag = db.diagnosis.find_one({'_id': get_objectid(diagnosis_id)})
        if diag is None:
            error(404, 'Invalid diagnosis')
        check_viewable(me, diag['patient'])

        inp = get_json({'name': str, 'medicine': list})
        if 'medicine' in inp:
            for med in inp['medicine']:
                if not isinstance(med, str):
                    error(400, 'Invalid input')

        db.diagnosis.update_one({'_id': get_objectid(diagnosis_id)}, {'$set': inp})
        return {'message': 'Updated diagnosis'}

    @route('/<string:diagnosis_id>/', methods=["DELETE"])
    def delete_diagnosis(self, diagnosis_id: str):
        me = get_login()
        if not me.get("is_doctor"):
            error(403, 'Only doctors can update diagnoses')
        diag = db.diagnosis.find_one({'_id': get_objectid(diagnosis_id)})
        if diag is None:
            error(404, 'Invalid diagnosis')
        check_viewable(me, diag['patient'])

        db.diagnosis.delete_one({'_id': get_objectid(diagnosis_id)})
        return {'message': 'Deleted diagnosis'}
