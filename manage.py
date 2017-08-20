#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>
#  

from init_file import create_app, db, User, Course, Department, Repository
from datetime import date

app = create_app()


@app.before_first_request
def before_first_request():
    db.drop_all()
    db.configure_mappers()
    db.create_all()

    cs = Department(name='Computer Science', faculty='CIS')
    mass_com = Department(name='Mass Communication', faculty='CIS')

    cpp = Course(name='C++', code='pdc709', lecturer_in_charge='Balogun, Mr.',
                 filename='sample_questions.json', date_to_be_held=date.today(),
                 duration_in_minutes=120, departments=[cs, mass_com])
    repo = Repository( repo_name='sproot', courses=[cpp] )
    user = User(username='iamOgunyinka', password='foobar', matric_staff_number='16/68HC014', role=4 )
    user.repositories.append( repo )

    db.session.add(user)
    db.session.add(cpp)
    db.session.add(cs)
    db.session.add(repo)
    db.session.add(mass_com)
    db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)
