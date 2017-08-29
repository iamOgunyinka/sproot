#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>
#  

from init_file import create_app, db, User

app = create_app()


@app.before_first_request
def before_first_request():
    # db.drop_all()
    db.configure_mappers()
    db.create_all()

    # db.session.add( User(role=4, username='iamOgunyinka', matric_staff_number='iamOgunyinka', password='foobar'))
    # db.session.commit()



if __name__ == '__main__':
    app.run(debug=True)
