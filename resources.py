#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>
#

from itsdangerous import TimedJSONWebSignatureSerializer as TJsonSerializer, SignatureExpired, BadSignature
from flask import url_for, jsonify
from flask_login import current_user
from functools import wraps, partial
from models import Course
import os
import redis


ERROR, SUCCESS = (0, 1)
UPLOAD_DIR = os.environ.get('FILES_DIR')
ADMINISTRATOR = 4
url_for = partial( url_for, _scheme='http' )
# well_known_courses is a map of most accessed courses and their owners/repository
well_known_repositories = {}
EXPIRY_INTERVAL = 60 * 60 * 12  # 12hours


cache_pass,port_number=os.environ.get('redis_pass'),int(os.environ.get('redis_port'))
data_cache = redis.StrictRedis(password=cache_pass,port=port_number)
pending_email_keys = 'tuq:pending_confirmation_emails'
pending_paper_keys = 'tuq:pending_papers'
well_known_courses = 'tuq:known_courses'


def send_confirmation_message(user_email, user_id, fullname ):
    data_cache.hset(pending_email_keys, user_email, '{} %% {}'.format(user_id,fullname))


def submit_paper_for_marking(user_email,data_string):
    data_cache.hset(pending_paper_keys, user_email, data_string)


def urlify(course_owner, repository, expiry):
    s = TJsonSerializer(os.environ.get('SECRET_KEY'), expires_in=expiry)
    token = s.dumps({'repo_name': repository.repo_name, 'staff_number': course_owner.username})
    return url_for('auth.raw_route', token=token, expires=expiry, _external=True)


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


def list_courses_data(owner, list_of_courses):
    my_list = []
    for course in list_of_courses:
        my_list.append(
            {'paper_name': course.name, 'paper_code': Course.generate_course_token(course.id,EXPIRY_INTERVAL), 
            'duration': course.duration_in_minutes, 'instructor': course.lecturer_in_charge,
            'departments': jsonify_departments(course.departments), 'randomize': course.randomize_questions,
            'owner': owner.username, 'reply_to': url_for('auth.post_secure_sesd_route', _external=True),
            'url': url_for('auth.get_paper_route', url=coursify(course.id, course.quiz_filename),
                _external=True)})
    return my_list


def jsonify_courses(owner, list_of_courses, date_from, date_to):
    courses = list_courses_data(owner, list_of_courses)
    return jsonify({'status': SUCCESS, 'exams': courses, 'from': str(date_from), 'cacheable': True,
                    'to': str(date_to)})


def respond_back(message_code, message_detail):
    return jsonify({'status': message_code, 'detail': message_detail})


def administrator_required(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if current_user.role < ADMINISTRATOR:
            return respond_back(ERROR, 'Only an admin is allowed to carry out this operation')
        return f(*args, **kwargs)

    return decorated_func


class MyJSONObjectWriter():
    def __init__(self):
        self.buffer = ''

    def write(self, new_string):
        self.buffer += new_string

    def get_buffer(self):
        return self.buffer

    def __repr__(self):
        return self.get_buffer()
