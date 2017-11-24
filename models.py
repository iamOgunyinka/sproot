#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager
from itsdangerous import TimedJSONWebSignatureSerializer as TJsonSerializer, SignatureExpired, BadSignature
from random import randint
import os

db = SQLAlchemy()
login_manager = LoginManager()

login_manager.session_protection = 'strong'
login_manager.login_view = 'main.login_route'
DEFAULT_DISPLAY_PICTURE = os.environ.get('DEFAULT_DP')


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False, index=True)
    fullname = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String( 128 ), unique = True, nullable = False, index = True)
    alias = db.Column(db.String( 128 ), unique = False, nullable = True, index = False)
    password_hash = db.Column(db.String(128), index=True, nullable=True)
    role = db.Column(db.Integer, nullable=False)
    phone_number = db.Column( db.String(128), index=True, nullable=False, unique=True)
    address = db.Column(db.Text, nullable = False)
    other_info = db.Column(db.Text, nullable = True)
    display_picture = db.Column(db.Text, nullable = False)
    is_active_premium = db.Column(db.Boolean, index = True)
    is_confirmed = db.Column(db.Boolean, default=False)
    payment_info = db.relationship('PaymentInformation', backref='premium_details')
    repositories = db.relationship('Repository', backref='user_repo')

    SUPER_USER = 0x8
    ADMINISTRATOR = 0x4
    NORMAL_USER = 0x2
    
    @property
    def password(self):
        raise AttributeError('Cannot get plain password')

    @password.setter
    def password(self, data):
        self.password_hash = generate_password_hash(data)
        
    @property
    def confirmed(self):
        return self.is_confirmed
    
    def verify_password(self, passwd):
        return check_password_hash(self.password_hash, passwd)

    def __repr__(self):
        return '<User %r>' % self.matric_staff_number
    
    @staticmethod
    def generate_confirmation_token( email, user_id, expiry ):
        s = TJsonSerializer( os.environ.get( 'SECRET_KEY' ), expires_in = expiry )
        return s.dumps({'endUsers': str( email ), 'id': user_id })
    
    @staticmethod
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
        except:
            return None
    
    @staticmethod
    def confirm_user_with_token( expiry, token ):
        data_obtained = User.get_data( expiry, token )
        if data_obtained is None:
            return data_obtained
        # by the time we're here, data_obtained is guaranteed to not be None
        user = db.session.query( User ).filter_by(email=unicode(data_obtained.get('endUsers'))).first()
        if user is None or user.id != data_obtained.get('id') or user.is_confirmed:
            return None

        user.is_confirmed = True
        db.session.add( user )
        db.session.commit()
        return user

class AnonymousUser( AnonymousUserMixin ):
    @property
    def confirmed( self ):
        return False

login_manager.anonymous_user = AnonymousUser


class PaymentInformation( db.Model ):
    __tablename__ = 'premium_users'
    id = db.Column( db.Integer, primary_key = True )
    user_id = db.Column( db.Integer, db.ForeignKey( 'users.id' ) )
    date_commenced = db.Column( db.DateTime, nullable = False )
    payment_logs = db.Column( db.Text, nullable = False )


class Repository( db.Model ):
    __tablename__ = 'repositories'
    
    id = db.Column( db.Integer, primary_key = True )
    repo_name = db.Column(db.String(128), nullable=False, unique=False)
    courses = db.relationship('Course', backref='repo')
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __repr__(self):
        return '<Repository {name}, {id}>'.format(name=self.repo_name,id=self.id)


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String(128), nullable=False)
    code = db.Column(db.String(32), nullable=False, unique=False)
    lecturer_in_charge = db.Column(db.String(128), nullable=False)
    departments = db.relationship('Department', backref='course')
    quiz_filename = db.Column(db.Text, nullable=False)
    solution_filename = db.Column( db.Text, nullable =False)
    date_to_be_held = db.Column(db.Date, nullable=False)
    expires_on = db.Column( db.Date, nullable = True )
    duration_in_minutes = db.Column(db.Integer, nullable=False)
    randomize_questions = db.Column( db.Boolean, nullable = False )
    answers_approach = db.Column( db.SmallInteger, nullable = False )
    repo_id = db.Column(db.Integer, db.ForeignKey('repositories.id'))
    
    TRADITIONAL_ANSWER_APPROACH = 0x1
    MODERN_ANSWER_APPROACH = 0x2
    HYBRID_ANSWER_APPROACH = 0X4
    
    def __repr__(self):
        return "<Course ==> ID: {}, code: {}>".format(self.id, self.code)
    
    @staticmethod
    def generate_course_token(course_id, expiry):
        s = TJsonSerializer( os.environ.get( 'SECRET_KEY' ), expires_in = expiry )
        return s.dumps({'end_user': str(randint(1, 300000)), 'id': course_id })
    
    @staticmethod
    def get_course_id(token, time_expire):
        data = User.get_data(time_expire,token)
        if data is None:
            return data
        return int(data.get('id'))


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=False, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))


class ExamTaken(db.Model):
    __tablename__ = 'exams_taken'
    id = db.Column(db.Integer, primary_key=True, index = True)
    course_owner = db.Column(db.Integer, index=False, nullable=False, unique=False)
    course_id = db.Column(db.Integer, nullable=False)
    participant_id = db.Column(db.Integer, index = True, nullable = False)
    date_taken = db.Column(db.Date, nullable=False)
    other_data = db.Column(db.Text)
    score = db.Column(db.Integer, nullable=False)


    def __repr__(self):
        return '<ExamTaken Matriculation number = {number}, Course Code: {code}>'\
            .format(number=self.matric_number, code=self.course_code)


@login_manager.user_loader
def load_user( user_id ):
    return User.query.get( int( user_id ) )
