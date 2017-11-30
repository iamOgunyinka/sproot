#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  admin_broker.py
#  
#  Copyright 2017 Josh <Josh@JOSHUA>

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import ExamTaken, Course
from threading import Thread
from datetime import datetime
import os
import redis
import time
import json


cache_pass, port_number = os.environ.get('redis_pass'), int(os.environ.get('redis_port'))
data_cache = redis.StrictRedis(password=cache_pass, port=port_number)
# sleep_time = 60 * 60 * 2 # 2 hours
sleep_time = 60
pending_paper_key = 'tuq:pending_papers'
error_marking_key = 'tuq:error_unmarked_papers'


def create_app():
    application = Flask(__name__)

    application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    application.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL')
    application.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    return application


def grab_course_data(course_id, database_handle):
    course = database_handle.session.query(Course).filter_by(id=course_id).first()
    if course is None:
        raise ValueError('Course data is \'None\' for ID: {}'.format(course_id))
    return course


def mark_paper(course_data, user_solution_array):
    """
    :param user_solution_array: should be an array of index integers with length
    EXACTLY == solutions data length.
    :param course_data: should be the database query result holding information on
    the course to be marked, including its unique ID.
    """
    soltn_file_data = open(course_data.solution_filename, 'r')
    actual_solution_data = json.load(soltn_file_data)
    soltn_file_data.close()
    arity = len(actual_solution_data)
    if arity != len(user_solution_array):
        raise ValueError('Unequal data length for course {} with ID: {}'
                         .format(course_data.name, course_data.id))
    score = 0
    for i in range(0, arity):
        if int(actual_solution_data[i]) == int(user_solution_array[i]):
            score += 1
    return score, arity


app = create_app()
db = SQLAlchemy()
db.init_app(app)


def main(logger):
    time.sleep(10)
    with app.app_context():
        while True:
            paper_keys = data_cache.hgetall(pending_paper_key).keys()
            if len(paper_keys) == 0:
                logger.flush()
                time.sleep(sleep_time)
            for user_paper in paper_keys:
                user_data_string = data_cache.hget(pending_paper_key, user_paper)
                user_data_object = json.loads(user_data_string)

                user_answers_string = user_data_object.get('data')
                user_solution_object = json.loads(user_answers_string)
                course_id = long(user_data_object.get('course_id'))
                user_id = long(user_data_object.get('user_id'))
                owner_id = long(user_data_object.get('owner_id'))
                date_taken = user_data_object.get('date_taken')

                try:
                    course_data = grab_course_data(course_id, db)
                    score, total = mark_paper(course_data, user_solution_object)
                    exam_taken = ExamTaken(course_id=course_id, participant_id=user_id,
                                           date_taken=date_taken, other_data=user_answers_string,
                                           score=score, course_owner=owner_id, total_score=total)
                    db.session.add(exam_taken)
                    db.session.commit()
                except Exception as exc:
                    logger.write('{}: Error({}): {}\n'.format(datetime.utcnow(), user_paper, str(exc)))
                    data_cache.hset(error_marking_key, user_paper, user_data_string)
                data_cache.hdel(pending_paper_key, user_paper)


event_logger = open('./logs.txt', 'a')
new_thread = Thread(target=main, args=[event_logger])
new_thread.setDaemon(True)
new_thread.start()

if __name__ == '__main__':
    app.run(port=3457, debug=True)
