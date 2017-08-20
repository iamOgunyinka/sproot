#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>
#  

from flask import Blueprint
from flask import Flask
from flask_mail import Mail
from flask_moment import Moment
from models import db, User, Department, Course, Repository
import os


moment = Moment()
mail = Mail()


def create_app():
    app = Flask( __name__ )
    app.config['SECRET_KEY'] = os.environ.get( 'SECRET_KEY' )
    app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get( 'WTF_KEY' )
    app.config['SQLALCHEMY_DATABASE_URI' ] = os.environ.get( 'DB_URL' )
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    
    moment.init_app( app )
    db.init_app( app )
    mail.init_app( app )
    
    from models import login_manager
    login_manager.init_app( app )
    
    from views import main, auth
    app.register_blueprint( main )
    app.register_blueprint( auth, url_prefix = '/auth' )
    
    return app
