#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager


db = SQLAlchemy()
login_manager = LoginManager()

login_manager.session_protection = 'strong'
login_manager.login_view = 'main.login_route'


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False, index=True)
    matric_staff_number = db.Column(db.String(128), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(128), index=True, nullable=True)
    role = db.Column(db.Integer, nullable=False)
    repositories = db.relationship( 'Repository', backref='user_repo' )

    ADMINISTRATOR = 0x4
    NORMAL_USER = 0x2
    
    @property
    def password(self):
        raise AttributeError('Cannot get plain password')

    @password.setter
    def password(self, data):
        self.password_hash = generate_password_hash(data)

    def verify_password(self, passwd):
        return check_password_hash(self.password_hash, passwd)

    def __repr__(self):
        return '<User %r>' % self.matric_staff_number


class Repository( db.Model ):
    __tablename__ = 'repositories'
    
    id = db.Column( db.Integer, primary_key = True )
    repo_name = db.Column(db.String(128), nullable=False, unique=False)
    courses = db.relationship('Course', backref='repo')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __repr__(self):
        print '<Repository {name}, {id}>'.format(name=self.repo_name,id=self.id)


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    code = db.Column(db.String(32), nullable=False, index=True, unique=False)
    lecturer_in_charge = db.Column(db.String(128), nullable=False)
    departments = db.relationship('Department', backref='course')
    filename = db.Column(db.Text, nullable=False)
    date_to_be_held = db.Column(db.Date, nullable=False)
    duration_in_minutes = db.Column(db.Integer, nullable=False)
    repo_id = db.Column(db.Integer, db.ForeignKey('repositories.id'))

    def __repr__(self):
        return "<Course name: %r, code: %r" % (self.name, self.code)


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=False, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))


class ExamTaken(db.Model):
    __tablename__ = 'exams_taken'
    id = db.Column(db.Integer, primary_key=True)
    matric_number = db.Column(db.String(64), nullable=False)
    course_code = db.Column(db.String(64), nullable=False)
    date_taken = db.Column(db.Date, nullable=False)
    other_data = db.Column(db.LargeBinary)

    def __repr__(self):
        return '<ExamTaken Matriculation number = {number}, Course Code: {code}>'\
            .format(number=self.matric_number, code=self.course_code)


@login_manager.user_loader
def load_user( user_id ):
    return User.query.get( int( user_id ) )
