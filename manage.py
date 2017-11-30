#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>
#  

from init_file import create_app, db
from flask_migrate import Migrate


app = create_app()
migrate = Migrate(app, db)

@app.before_first_request
def before_first_request():
    db.configure_mappers()
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
