#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>


from flask import Blueprint, jsonify, request, redirect, url_for, send_file, safe_join
from werkzeug.exceptions import BadRequest
from datetime import date
from models import db, User, Course, ExamTaken, Department, Repository
from resources import urlify, get_data, respond_back, jsonify_courses, administrator_required
from resources import ERROR, SUCCESS, UPLOAD_DIR, list_courses_data
from random import randint
from flask_login import login_required, login_user, current_user
import json, os


main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
EXT = '.silt'

def invalid_url_error():
    return respond_back(ERROR, 'Invalid URL specified')


def safe_makedir( parent_path, path, paths=''):
    user_directory = os.path.join(parent_path, safe_join( path, paths))
    if not os.path.exists(user_directory):
        os.makedirs(user_directory)
    return user_directory


@main.route('/<username>/<repo>{ext}'.format(ext=EXT))
def initial_request_route(username, repo):
    local_usr = db.session.query(User).filter_by(username=username).first()
    if local_usr is None or local_usr.role != User.ADMINISTRATOR:
        return respond_back(ERROR, 'User does not exists or repository name is invalid')
    repositories = local_usr.repositories
    for repository in repositories:
        if repository.repo_name == repo:
            return jsonify({'status': SUCCESS, 'url': urlify(local_usr, repository, 60 * 60 * 2), 'detail': 'Success'})
    return respond_back( ERROR, 'Invalid repository name' )


@main.route('/')
def main_route():
    endpoints = {
        'login_to': url_for( 'main.login_route', _external=True ),
        'add_user': url_for( 'auth.add_user_route', _external=True ),
        'add_admin': url_for( 'auth.add_admin_route', _external=True ),
        'add_repository': url_for( 'auth.add_repository_route', _external=True),
        'add_course': url_for( 'auth.admin_add_course_route', _external=True),
        'get_repositories': url_for( 'auth.get_repositories_route', _external=True),
        'get_courses': url_for( 'auth.get_courses_route', _external=True)
    }
    return jsonify( {'status': SUCCESS, 'endpoints': endpoints})


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
    repository = db.session.query( Repository ).filter_by( user_id = user.id, repo_name = data.get('repo_name')).first()
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
    return jsonify_courses(list_of_courses, date_range_from, date_range_to)


@main.app_errorhandler(404)
def error_404(e):
    return invalid_url_error()


@main.app_errorhandler(500)
def interval_server_error(e):
    return respond_back(ERROR,'An internal server error occured')


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
    return send_file( course.filename)


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


@auth.route('/add_admin', methods=['POST'])
@login_required
@administrator_required
def add_admin_route():
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
            
        repository = Repository( repo_name = repository_name )
        new_user = User(username=username, password=password, matric_staff_number=staff_number,
                        role=User.ADMINISTRATOR, repositories=[repository])
        safe_makedir( UPLOAD_DIR, username, repository_name )
        db.session.add(repository)
        db.session.add(new_user)
        db.session.commit()
        return respond_back(SUCCESS, 'User created successfully')
    except BadRequest as b:
        return respond_back(ERROR, 'Bad request')
    except Exception as e:
        return respond_back(ERROR, 'Unable to add user, check the data and try again')


@auth.route( '/add_user', methods=['POST'] )
@login_required
@administrator_required
def add_user_route():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if username is None or password is None:
            return respond_back(SUCCESS, 'Missing arguments')
        user = User.query.filter_by(username=username).first()
        if user is not None:
            return respond_back(ERROR, 'Username already exist')
        user=User(username=username, password=password,matric_staff_number=username,
                  role=User.NORMAL_USER)
        db.session.add(user)
        db.session.commit()
        return respond_back(SUCCESS,'User has been successfully added')
    except BadRequest as b:
        return respond_back(ERROR, str(b))
    except Exception as e:
        return respond_back(ERROR, str(e))


@auth.route( '/add_repository', methods = ['POST'] )
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
        user_repositories = current_user.repositories
        for repo in user_repositories:
            if repo.repo_name == repository_name:
                return respond_back( ERROR, 'Repository with that name already exist in your account')
        repository = Repository( repo_name = repository_name )
        current_user.repositories.append( repository )

        safe_makedir(UPLOAD_DIR, current_user.username, repository_name )

        db.session.add( repository )
        db.session.add( current_user )
        db.session.commit()
        return respond_back(SUCCESS,'Successful')
    except BadRequest:
        return respond_back(ERROR, 'Bad request')
    except Exception as e:
        print e
        return respond_back(ERROR, 'Unable to add repository, check the data and try again')


@auth.route('/admin_add_course', methods=['POST'])
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
        approach = data.get( 'approach' )
        randomize_question = data.get( 'randomize' )
        expires = data.get( 'expires_on' )
        sign_in_required = data.get( 'sign_in_required', False )
        
        # Array of name:faculty objects
        departments = data.get('departments')
        repository_name = data.get( 'repository_name' )
        
        if course_code is None or course_name is None or personnel_in_charge is None or \
                        hearing_date is None or duration_in_minutes is None or departments is None or \
                        question_location is None or randomize_question is None or approach is None:
            return respond_back(ERROR, 'Missing arguments')
        
        repositories = current_user.repositories
        repository_to_use = None
        for repo in repositories:
            if repo.repo_name == repository_name:
                repository_to_use = repo
                break
        
        if repository_to_use is None:
            return respond_back(ERROR, 'Repository does not exist')
        for course in repository_to_use.courses:
            if course_code == course.code:
                return respond_back(ERROR, 'Course with that code already exist')
        
        department_list = []
        try:
            for department_name in departments:
                department_list.append(Department( name = department_name ))
        except AttributeError:
            return respond_back(ERROR, 'Expects a valid data in the departments')
        
        full_path = None
        try:
            filename = course_code.replace( ' ', '_' ).replace( '.', '_' ) + '.json'
            dir_path = safe_makedir( UPLOAD_DIR, current_user.username, repository_name )
            full_path = safe_join( dir_path, filename )

            with open(full_path,mode='wt') as out:
                json.dump( question_location, out, sort_keys=True, indent=4, separators=(',', ': '))
            
        except ValueError:
            return respond_back(ERROR,'Invalid JSON Document for question' )
        course = Course(name=course_name, code=course_code, lecturer_in_charge=personnel_in_charge, 
                        answers_approach = approach, expires_on = expires, sign_in_required = sign_in_required,
                        date_to_be_held=date_from_string(hearing_date), duration_in_minutes=int(duration_in_minutes),
                        departments=department_list, filename =full_path, randomize_questions =randomize_question )
        
        repository_to_use.courses.append( course )
        
        db.session.add(course)
        db.session.add(repository_to_use)
        db.session.add(current_user)        
        
        db.session.commit()
        return respond_back(SUCCESS, 'New course added successfully')
    except BadRequest:
        return respond_back(ERROR, 'Bad request')
    except Exception as e:
        print e
        return respond_back(ERROR, 'Could not add the course')


@auth.route( '/get_repositories' )
@login_required
@administrator_required
def get_repositories_route():
    repositories = [ { 'name': repository.repo_name, 
        'url': '{url}{username}/{repo}{ext}'.format( url=
            url_for( 'main.main_route', _external=True), username=current_user.username,repo=repository.repo_name,ext=EXT),
        'courses': [ course.name for course in repository.courses ] } for repository in current_user.repositories]
    return jsonify({'status': 1, 'repositories': repositories, 'detail': 'Successful' } )


@auth.route('/get_courses_from_repo' )
@login_required
@administrator_required
def get_courses_route():
    try:
        repository_name = request.args.get('repository')
        if repository_name is None:
            return respond_back(ERROR,'Invalid repository name')
        repository = db.session.query(Repository).filter_by(user_id=current_user.id, repo_name=repository_name).first()
        if repository is None:
            return respond_back(ERROR,'Nothing found')
        return jsonify({'status':SUCCESS, 'courses': list_courses_data(repository.courses)})
    except BadRequest:
        return respond_back(ERROR, 'Bad request')


@auth.before_request
def before_auth_request():
    if not current_user.is_authenticated:
        return respond_back(ERROR, 'Not logged in')
