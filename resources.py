#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>
#

from itsdangerous import TimedJSONWebSignatureSerializer as TJsonSerializer, SignatureExpired, BadSignature
from flask import url_for, jsonify
from flask_login import current_user
from functools import wraps
import os

ERROR, SUCCESS = (0, 1)
UPLOAD_DIR = os.environ.get('UPLOAD_DIR')
ADMINISTRATOR = 4

def urlify(local_user, repository, expiry):
    s = TJsonSerializer(os.environ.get('SECRET_KEY'), expires_in=expiry)
    token = s.dumps({'repo_name': repository.repo_name, 'staff_number': local_user.matric_staff_number})
    return url_for('main.raw_route', token=token, expires=expiry, _external=True)


def get_data(expiry, token):
    if token is None:
        return token

    serializer = TJsonSerializer(os.environ.get('SECRET_KEY'), expires_in=expiry)
    try:
        data = serializer.loads(token)
        return data
    except SignatureExpired:
        return None
    except BadSignature:
        return None


def coursify(course_id, location):
    s = TJsonSerializer(os.environ.get('SECRET_KEY'), expires_in=60 * 60)
    return s.dumps({'id': course_id, 'location': location})


def jsonify_departments(departments):
    list_of_department = []
    for department in departments:
        list_of_department.append(department.name)
    return list_of_department


def jsonify_courses(list_of_courses, date_from, date_to):
    my_list = []
    for course in list_of_courses:
        my_list.append(
            {'paper_name': course.name, 'paper_code': course.code.upper(), 'duration': course.duration_in_minutes,
             'departments': jsonify_departments(course.departments), 'instructor': course.lecturer_in_charge,
             'url': url_for('main.get_paper_route', url=coursify(course.id, course.question_location),
                            _external=True)})
    return jsonify({'status': SUCCESS, 'exams': my_list, 'from': str(date_from),
                    'to': str(date_to), 'reply_to': url_for('auth.post_data_route', _external=True),
                    'login_through': url_for('main.login_route', _external=True)})


def respond_back(message_code, message_detail):
    return jsonify({'status': message_code, 'detail': message_detail})


def administrator_required(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if current_user.role != ADMINISTRATOR:
            return respond_back(ERROR, 'Only an admin is allowed to carry out this operation')
        return f(*args, **kwargs)

    return decorated_func
