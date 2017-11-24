#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>
#  

from flask import Flask
from flask_moment import Moment
from models import db
from flask_uploads import configure_uploads, patch_request_class
from flask_bootstrap import Bootstrap
#~ from flask_wtf.csrf import CSRFProtect
import os

moment = Moment()
bootstrap = Bootstrap()
#~ csrf = CSRFProtect()

def create_app():
    app = Flask( __name__ )
    app.config['SECRET_KEY'] = os.environ.get( 'SECRET_KEY' )
    app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get( 'WTF_KEY' )
    app.config['SQLALCHEMY_DATABASE_URI' ] = os.environ.get( 'DB_URL' )
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    
    # app.config['UPLOADS_DEFAULT_DEST'] = os.environ.get('UPLOAD_DIR')
    app.config['UPLOADS_DEFAULT_URL'] = os.environ.get('GENERAL_UPLOAD_URL')

    moment.init_app( app )
    db.init_app(app)
    bootstrap.init_app(app)
    #~ csrf.init_app( app )
    
    from models import login_manager
    login_manager.init_app( app )
    
    from views import main, auth
    from views import public_photos, public_raw_files
    app.register_blueprint(main,url_prefix='/tuq')
    app.register_blueprint(auth, url_prefix='/tuq/auth')
    configure_uploads( app, (public_photos,public_raw_files)) #configure photos and raw_files
    patch_request_class(app, size=1024*100) #100KB Max size
    
    return app
