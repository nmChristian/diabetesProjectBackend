"""
Author: Alexander
Description: Data endpoint, for operations on diagnoses
             Generally this is for basal, bolus, cgm, exercise and meals,
             but there's also an endpoint for updating "extra" single-time data.
"""
from typing import Optional

from fullstack import db, DEFAULT_GLYCEMIC_RANGES, DEFAULT_GLYCEMIC_TARGETS

from flask_classy import FlaskView, route
from fullstack.utils import jsonify, get_json, get_login, error, check_viewable
import datetime


ALL_TYPES = ['basal', 'bolus', 'cgm', 'exercise', 'meals']
NDAYS = 14


def parse_data_types(show):
    if show is None:
        show = ALL_TYPES
    out = set()
    for i in show:
        if i in ALL_TYPES:
            out.add(i)
    return list(out)


def check_distributions(dist, perc):
    out = []
    if dist[0] > perc[0]:
        out.append(0)
    if dist[0] + dist[1] > perc[1]:
        out.append(1)
    if dist[2] < perc[2]:
        out.append(2)
    if dist[3] + dist[4] > perc[3]:
        out.append(3)
    if dist[4] > perc[4]:
        out.append(4)
    return out


def get_patient_data(patient_id, show: list, start_time: datetime.datetime, end_time: datetime.datetime = None):

    condition = {'$gte': start_time}
    if end_time is not None:
        condition['$lt'] = end_time

    out = {}
    for col in show:
        data = db[col].find({'patient': patient_id, 'timestamp': condition},
                            {'value': 1, 'timestamp': 1, '_id': 0})
        out[col] = [{'t': int(d['timestamp'].timestamp()), 'v': d['value']} for d in data]
    return out


def get_range_idx(ranges: list, val: float):
    for i in range(len(ranges)):
        if val < ranges[i]:
            return i
    return len(ranges)


class DataView(FlaskView):

    @route('/get', methods=["POST"])
    @route('/<string:id_str>/get', methods=["POST"])
    def get_data(self, id_str: Optional[str] = None):
        me = get_login()
        patient_id = check_viewable(me, id_str)

        inp = get_json({'start_time': str, 'end_time': str, 'ndays': int, 'show': list})
        show = parse_data_types(inp.get('show'))

        start_time = None
        end_time = None
        if 'ndays' in inp:
            start_time = datetime.datetime.now() - datetime.timedelta(days=inp['ndays'])
        else:
            if 'start_time' in inp:
                try:
                    start_time = datetime.datetime.strptime(inp['start_time'], "%Y-%m-%d")
                except ValueError:
                    error(400, 'Invalid start time')
            else:
                error(400, "Missing 'start_time' or 'ndays' parameter")

            if 'end_time' in inp:
                try:
                    end_time = datetime.datetime.strptime(inp['start_time'], "%Y-%m-%d")
                except ValueError:
                    error(400, 'Invalid start time')
                end_time += datetime.timedelta(days=1)

        return jsonify(get_patient_data(patient_id, show, start_time, end_time))

    @route("/", methods=["POST"])
    def add_data(self):
        # TODO: Check data validity
        me = get_login()
        if me.get('is_doctor'):
            error(403, 'Only patients can upload data')

        inp = get_json({'type': str, 'value': float, 'timestamp': int}, required=True)
        t = datetime.datetime.fromtimestamp(inp["timestamp"])

        if inp["type"] not in ALL_TYPES:
            error(400, 'Invalid data type')

        db[inp["type"]].insert_one({'timestamp': t, 'patient': me.get("_id"), 'value': inp["value"]})
        return jsonify({'message': 'Added data'})

    @route("/previews", methods=["GET"])
    def get_previews(self):
        me = get_login()

        viewable = me.get("viewable") or []
        viewable.append(me.get('_id'))
        users = db.users.find({'_id': {'$in': viewable}, 'is_doctor': {'$ne': True}}, {'_id': 1, 'ranges': 1})
        show = ['cgm']
        start_time = datetime.datetime.now() - datetime.timedelta(days=NDAYS)

        # Delete outdated cache
        db.cache.delete_many({'ttl': {'$lt': datetime.datetime.now()}})

        out = []
        for patient in users:
            cache = db.cache.find_one({'patient': patient['_id']})
            if cache is None:
                ranges = patient.get('glycemic_ranges') or DEFAULT_GLYCEMIC_RANGES
                data = get_patient_data(patient['_id'], show, start_time)
                values = [0]*96
                counts = [0]*96
                dist = [0] * (len(ranges) + 1)
                curr_time = start_time.timestamp()
                end_time = data['cgm'][-1]['t']
                total_time = end_time - curr_time
                for d in data['cgm']:
                    # Calculate distribution
                    dt = d['t'] - curr_time
                    dist[get_range_idx(ranges, d['v'])] += dt/total_time
                    curr_time = d['t']

                    # Calculate means
                    t = datetime.datetime.fromtimestamp(d['t'])
                    idx = t.hour * 4 + t.minute // 15
                    values[idx] += d['v']
                    counts[idx] += 1
                for i in range(96):
                    try:
                        values[i] /= counts[i]
                    except ZeroDivisionError:
                        values[i] = None
                problems = check_distributions(dist, patient.get('glycemic_targets') or DEFAULT_GLYCEMIC_TARGETS)
                cache = {'patient': patient['_id'], 'values': values, 'distribution': dist, 'problems': problems,
                         'ttl': datetime.datetime.now() + datetime.timedelta(hours=12)}
                db.cache.insert_one(cache)
            out.append(cache)

        return jsonify(out)

    @route('/extra', methods=["PUT"])
    def put_extra(self):
        me = get_login()
        data = get_json({'HbA1c': None, 'weight': None, 'blood_pressure': None}, required=None)
        for i in data.values():
            if not isinstance(i, int) and not isinstance(i, float):
                error(400, 'Invalid input')
        data['timestamp'] = datetime.datetime.now()
        out = me.get('extra_data') or {}
        for i in data:
            out[i] = data[i]
        db.users.update_one({'_id': me.get('_id')}, {'$set':{'extra_data': out}})
        return jsonify({'message': 'Updated extra data'})
