#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  admin_broker.py
#  
#  Copyright 2017 Josh <Josh@JOSHUA>

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import User, DEFAULT_DISPLAY_PICTURE
from sqlalchemy.exc import InvalidRequestError, ProgrammingError, IntegrityError
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
admin_request_key = 'tuq:admin_requests'
failures_key = 'tuq:admin_request_fails'
pending_email_keys = 'tuq:pending_confirmation_emails'


def create_app():
    application = Flask(__name__)

    application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    application.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL')
    application.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    return application


def save_to_database(user_info, db_connector):
    this_user = User(fullname=user_info.get('fullname'), address=user_info.get('address'),
                     email=user_info.get('email'), phone_number=user_info.get('mobile'),
                     is_active_premium=False,is_confirmed=False, role=User.ADMINISTRATOR,
                     display_picture=DEFAULT_DISPLAY_PICTURE, username=user_info.get('username'),
                     alias=user_info.get('alias'), password=user_info.get('password'),
                     date_of_registration = str(datetime.utcnow()),
                     other_info='Nationality: {}'.format(user_info.get('nationality')))
    db_connector.session.add(this_user)
    db_connector.session.commit()
    return True, this_user.id


app = create_app()
db = SQLAlchemy()
db.init_app(app)


def main(logger):
    time.sleep(10)
    while True:
        user_keys = data_cache.hgetall(admin_request_key).keys()
        logger.write('Keys: {}\n'.format(str(user_keys)))
        if len(user_keys) == 0:
            logger.flush()
            time.sleep(sleep_time)
        for user_key in user_keys:
            data = data_cache.hget(admin_request_key, user_key)
            this_user_info = json.loads(data)
            try:
                with app.app_context():
                    result, user_id = save_to_database(this_user_info, db)
                    email = this_user_info.get('email')
                    phone_number = this_user_info.get('mobile')
                    data_cache.sadd('tuq:usernames', this_user_info.get('username'))
                    data_cache.sadd('tuq:emails', email)
                    if phone_number is not None and data_cache.sismember('tuq:phones',phone_number):
                        data_cache.sadd('tuq:phones', phone_number)
                    data_cache.hset(pending_email_keys, email, 
                            '{} %% {}'.format(user_id, this_user_info.get('fullname')))
            except Exception as exc:
                logger.write('Error ocurred[{}]: {}\n'.format(datetime.utcnow(),str(exc)))
                data_cache.hset(failures_key, user_key, data)
            data_cache.hdel(admin_request_key, user_key)


event_logger = open('./logs.txt', 'a')
new_thread = Thread(target=main, args=[event_logger])
new_thread.setDaemon(True)
new_thread.start()

if __name__ == '__main__':
    app.run(debug=True)
