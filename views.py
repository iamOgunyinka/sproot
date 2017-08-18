#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>


from flask import Blueprint, jsonify, request, redirect, url_for, send_from_directory, safe_join
from werkzeug.exceptions import BadRequest
from datetime import date
from models import db, User, Course, ExamTaken, Department, Repository
from resources import urlify, get_data, respond_back, jsonify_courses, administrator_required
from resources import ERROR, SUCCESS, UPLOAD_DIR
from random import randint
from flask_login import login_required, login_user, current_user
from json import loads

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)


def invalid_url_error():
    return respond_back(ERROR, 'Invalid URL specified')


@main.route('/<username>/<repo>.silt')
def initial_request_route(username, repo):
    local_usr = db.session.query(User).filter_by(username=username).first()
    if local_usr is None or local_usr.role is not User.ADMINISTRATOR:
        return respond_back(ERROR, 'User does not exists or repository name is invalid')
    repositories = local_usr.repositories
    for repository in repositories:
        if repository.repo_name == repo:
            return jsonify({'status': SUCCESS, 'url': urlify(local_usr, repository, 60 * 60 * 2), 'detail': 'Success'})
    return respond_back( ERROR, 'Invalid repository name' )


# to-do: Send meaningful paths back to user.
@main.route('/')
def main_route():
    return jsonify({'status': SUCCESS, 'detail': 'OK'})


def date_from_string(text):
    if text is None:
        return text
    split_text_string = text.split('-')
    if len(split_text_string) < 3:
        return None
    (year, month, day) = (int(split_text_string[0]), int(split_text_string[1]), int(split_text_string[2]))
    try:
        new_date = date(year, month, day)
        return new_date
    except ValueError:
        return None


@main.route('/raw/<token>')
def raw_route(token):
    expires = request.args.get('expires', None)
    if expires is None:
        return invalid_url_error()
    data = get_data(expires, token)
    if data is None:
        return invalid_url_error()
    user = db.session.query(User).filter_by(matric_staff_number=data.get('staff_number', None)).first()
    if user is None:
        return invalid_url_error()
    repository = db.session.query( Repository ).filter( user_id == user.id, repo_name = data.get('repo_name')).first()
    if repository is None:
        return invalid_url_error()

    date_range_from = date_from_string(request.args.get('date_from', None))
    date_range_to = date_from_string(request.args.get('date_to', None))
    if date_range_from is None:
        date_range_from = date.today()
    if date_range_to is None:
        date_range_to = date.today()

    list_of_courses = db.session.query(Course).filter(Course.date_to_be_held >= date_range_from,
                                                      Course.date_to_be_held <= date_range_to,
                                                      Course.repo_id == repository.id ).all()
    print list_of_courses
    return jsonify_courses(list_of_courses, date_range_from, date_range_to)


@main.errorhandler(404)
def error_404(e):
    return invalid_url_error()


@main.route('/get_paper')
def get_paper_route():
    data = get_data(60 * 60, request.args.get('url', None))
    if data is None:
        return invalid_url_error()
    fileid = data.get('id')
    random_number = randint(1, 300000)  # just a random number to trick smart hackers thinking its useful
    return redirect(url_for('main.get_data_route', file_id=fileid, path=str(random_number), _external=True))


@main.route('/get_data')
def get_data_route():
    file_id = request.args.get('file_id', None)
    if file_id is None:
        return invalid_url_error()
    course = db.session.query(Course).filter_by(id=file_id).first()
    if course is None:
        return invalid_url_error()
    return send_from_directory(directory=UPLOAD_DIR, filename=course.question_location)


@auth.route('/post_data', methods=['POST'])
@login_required
def post_data_route():
    try:
        data = request.get_json()
        matriculation_number = data.get('matric_number', None)
        course_code = data.get('course_code', None)
        date_taken = data.get('date_taken', None)
        if matriculation_number is None or course_code is None or date_taken is None:
            return respond_back(ERROR, 'One of the primary arguments are missing')
        course_already_taken = db.session.query(ExamTaken).filter_by(matric_number=matriculation_number,
                                                                     course_code=course_code).first()
        print course_already_taken
        if course_already_taken is not None:
            return respond_back(ERROR, 'You have already taken this examination')
        exam_taken = ExamTaken(matric_number=matriculation_number, course_code=course_code,
                               date_taken=date_from_string(date_taken), other_data=str(data.get('answer_pair', None)))
        db.session.add(exam_taken)
        db.session.commit()
        return respond_back(SUCCESS, 'OK')
    except BadRequest:
        return respond_back(ERROR, 'No data was specified')


@main.route('/user_login', methods=['POST'])
def login_route():
    try:
        data = request.get_json()
        matric_number = data.get('username', None)
        password = data.get('password', None)
        course = data.get('course', None)

        student = db.session.query(User).filter_by(matric_staff_number=matric_number).first()
        if student is None:
            return jsonify({'status': ERROR, 'detail': 'Invalid login detail'})
        if not student.verify_password(password):
            return jsonify({'status': ERROR, 'detail': 'Invalid username or password'})
        login_user(student, False)
        return jsonify({'status': SUCCESS, 'detail': 'Logged in'})
    except BadRequest:
        return respond_back(ERROR, 'Invalid login request received.')


@main.route('/add_admin', methods=['POST'])
def add_user_route():
    try:
        data = request.get_json()
        username = data.get('username')
        staff_number = data.get('staff_number')
        password = data.get('password')
        repository_name = data.get('repository')
        if data is None or username is None or staff_number is None or \
                        password is None or repository_name is None:
            return respond_back(ERROR, 'Invalid data or missing data arguments')
        old_user = User.query.filter_by(username=username).first()
        if old_user is not None:
            return respond_back(ERROR, 'User already exist')
        new_user = User(username=username, password=password, matric_staff_number=staff_number,
                        role=User.ADMINISTRATOR, repo_name=repository_name, courses=[])
        db.session.add(new_user)
        db.session.commit()
        return respond_back(SUCCESS, 'User created successfully')
    except BadRequest:
        return respond_back(ERROR, 'Bad request')
    except:
        return respond_back(ERROR, 'Unable to add user, check the data and try again')


@main.route( '/add_repository', methods = 'POST' )
@login_required
@administrator_required
def add_repository_route():
    try:
        data = request.get_json()
        if data is None:
            return respond_back(ERROR, 'Invalid data')
        repository_name = data.get( 'repository_name' )
        if repository_name is None or len( repository_name ) == 0:
            return respond_back(ERROR, 'Invalid repository name supplied')
        if db.session.query(Repository).filter_by(repo_name = repository_name).first() is not None:
            return respond_back( ERROR, 'Repository with that name already exist in your account')
        repository = Repository( repo_name = repository_name )
        db.session.add( repository )
        db.session.commit()
        return respond_back(SUCCESS,'Successful')
    except BadRequest:
        return respond_back(ERROR, 'Bad request')
    except:
        return respond_back(ERROR, 'Unable to add repository, check the data and try again')


@main_route('/admin_add_course', methods=['POST'])
@login_required
@administrator_required
def admin_add_course_route():
    try:
        data = request.get_json()
        if data is None:
            return respond_back(ERROR, 'Invalid data')
        course_name = data.get('name')
        course_code = data.get('course_code')
        personnel_in_charge = data.get('administrator_name')
        hearing_date = data.get('date_to_be_held')
        duration_in_minutes = data.get('duration')
        question_location = data.get('question')
        # Array of name:faculty objects
        departments = data.get('departments')

        if course_code is None or course_name is None or personnel_in_charge is None or \
                        hearing_date is None or duration_in_minutes is None or departments is None or \
                        question_location is None:
            return respond_back(ERROR, 'Missing arguments')
        if db.session.query(Course).filter_by(code=course_code).first() is not None:
            return respond_back(ERROR, 'Course with the same course code already exist')
        department_list = []
        try:
            for i in departments:
                department_list.append(Department(name=i.get('name'), faculty=i.get('faculty')))
        except AttributeError:
            return respond_back(ERROR, 'Expects a valid data in the departments')
        filename = course_code + '.json'
        try:
            question_file = loads( question_location )
            full_path = safe_join( UPLOAD_DIR, filename )
            new_file = open(full_path,mode='w')
            new_file.write(question_file)
            new_file.close()
        except ValueError:
            return respond_back(ERROR,'Invalid JSON Document for question' )
        course = Course(name=course_name, code=course_code, lecturer_in_charge=personnel_in_charge,
                        date_to_be_held=date_from_string(hearing_date), duration_in_minutes=int(duration_in_minutes),
                        departments=department_list, filename =filename)
        db.session.add(course)
        db.session.commit()
        return respond_back(SUCCESS, 'New course added successfully')
    except BadRequest:
        return respond_back(ERROR, 'Bad request')


@auth.before_request
def before_auth_request():
    if not current_user.is_authenticated:
        return respond_back(ERROR, 'Not logged in')
