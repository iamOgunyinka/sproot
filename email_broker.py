#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  email_broker.py
#  
#  Copyright 2017 Josh <ogunyinkajoshua@gmail.com>

from flask import Flask, render_template
from itsdangerous import TimedJSONWebSignatureSerializer as TJsonSerializer
from flask_mail import Message, Mail
from sqlalchemy.exc import InvalidRequestError, ProgrammingError, IntegrityError
from threading import Thread
import os, redis, time, json


cache_pass,port_number=os.environ.get('redis_pass'),int(os.environ.get('redis_port'))
data_cache = redis.StrictRedis(password=cache_pass,port=port_number)
sleep_time = 60 * 10# every 10 minutes

failed_confirmation_emails = 'tuq:failed_confirmation_emails'
pending_confirmation_emails = 'tuq:pending_confirmation_emails'
FROM_MAIL='[Tuq]The Universal Quiz Network'
COMPANY_NAME = 'Tuq'
EXPIRY_INTERVAL = 60 * 60 * 12 #12hours


def create_app():
    app = Flask( __name__ )

    app.config['SECRET_KEY'] = os.environ.get( 'SECRET_KEY' )
    app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    return app


def generate_confirmation_token(email, user_id, expiry):
    s = TJsonSerializer(os.environ.get('SECRET_KEY'), expires_in=expiry)
    return s.dumps({'endUsers': str(email), 'id': user_id })


def send_mail(to_mail,subject, message_body):
    message = Message(subject, sender=FROM_MAIL, recipients=[to_mail])
    message.body = message_body
    mail.send(message)


def send_confirmation_message(user_email, user_id, fullname, expiry):
    token = generate_confirmation_token(user_email, user_id, expiry)
    link_url = 'https://sproot.xyz/tuq/confirm?token={}'.format(token)
    
    body = render_template('end_user_confirm.txt', full_name=fullname, 
        company=COMPANY_NAME, link_url=link_url)
    send_mail(user_email, subject='[Tuq] Confirm your email account',message_body=body)



app = create_app()
mail = Mail()
mail.init_app(app)


def main():
    time.sleep( 5 )
    with app.app_context():
        while(True):
            mail_receivers = data_cache.hgetall(pending_confirmation_emails).keys()
            if len(mail_receivers) == 0:
                time.sleep(sleep_time)
            for mail_receiver in mail_receivers:
                receiver_info = data_cache.hget(pending_confirmation_emails,mail_receiver)
                receiver_id, fullname = (receiver_info[0], receiver_info[1])
                try:
                    send_confirmation_message(mail_receiver, receiver_id, fullname, EXPIRY_INTERVAL)
                except Exception as e:
                    print e
                    data_cache.hset(failed_confirmation_emails,mail_receiver, receiver_id)
                data_cache.hdel(pending_confirmation_emails, mail_receiver)


if __name__ == '__main__':
    new_thread = Thread(target=main, args=[])
    new_thread.setName('ConfirmationEmailSenderDaemon')
    new_thread.setDaemon(True)
    new_thread.start()
    app.run(port=8766)
