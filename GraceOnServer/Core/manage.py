#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>
#  

from init_file import create_app, db
from models import User, DEFAULT_DISPLAY_PICTURE
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db)

@app.before_first_request
def before_first_request():
#    db.drop_all()
    db.configure_mappers()
    db.create_all()

#    db.session.add( User(
#        fullname='Joshua Ogunyinka', address='Nigeria',email='ogunyinkajoshua@yahoo.com',
#        phone_number='+234-703-350-0593',is_active_premium=True,is_confirmed=True,
#        display_picture=DEFAULT_DISPLAY_PICTURE,
#        role=User.SUPER_USER, username='iamOgunyinka',alias='iamOgunyinka', password='foobar'))
#    db.session.commit()



if __name__ == '__main__':
    app.run()
