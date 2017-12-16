#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>


from flask import Blueprint, jsonify, request, redirect, send_file, safe_join, render_template, flash, session
from werkzeug.exceptions import BadRequest
from datetime import date, datetime
from sqlalchemy.exc import InvalidRequestError
from models import db, User, Course, ExamTaken, Department, Repository, DEFAULT_DISPLAY_PICTURE
from resources import urlify, get_data, respond_back, jsonify_courses, administrator_required, Links, coursify
from resources import ERROR, SUCCESS, UPLOAD_DIR, list_courses_data, MyJSONObjectWriter, EXPIRY_INTERVAL
from resources import send_confirmation_message, submit_paper_for_marking, url_for, well_known_courses
from forms import data_cache, AdminRequestForm
from random import randint
from flask_login import login_required, login_user, current_user
from flask_uploads import UploadSet, UploadNotAllowed, IMAGES, TEXT, DOCUMENTS, DATA
import json
import os

RAW_FILES = TEXT + DOCUMENTS + DATA
EXT = '.silt'

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
web = Blueprint('web', __name__)

public_photos = UploadSet('photos', IMAGES, default_dest=lambda app: os.environ.get('GENERAL_UPLOAD_DIRECTORY'))
public_raw_files = UploadSet('rawFiles', RAW_FILES, default_dest=lambda app: os.environ.get('GENERAL_UPLOAD_DIRECTORY'))
premium_photos = UploadSet( 'PremiumPhotos', IMAGES, default_dest=lambda app: os.environ.get('PREMIUM_UPLOAD_DIRECTORY'))
premium_raw_files = UploadSet( 'PremiumRawFiles', RAW_FILES, default_dest=lambda app: os.environ.get('PREMIUM_UPLOAD_DIRECTORY') )
known_clients = ('TuqOnPC', 'TuqOnMobile')
all_course_ranks = 'tuq:all_course_rank'
deleted_repo_keys = 'tuq:deleted_repos'
deleted_course_keys = 'tuq:deleted_courses'


internal_url_for = url_for

def error_response(message):
    return respond_back(ERROR, message)


def success_response(message):
    return respond_back(SUCCESS, message)


def invalid_url_error():
    return error_response('Invalid URL specified')


def safe_makedir(parent_path, path, paths=''):
    user_directory = os.path.join(parent_path, safe_join(path, paths))
    if not os.path.exists(user_directory):
        os.makedirs(user_directory)
    return user_directory


def rank_courses_result(courses):
    data = []
    # courses = json.loads(courses)
    for course in courses:
        course = json.loads(course)
        if course is None: continue
        course_id = long(course.get('id'))
        data.append({
            'paper_name': course.get('name'),
            'id': Course.generate_course_token(course_id,EXPIRY_INTERVAL*2),
            'owner': course.get('owner'), 'icon': course.get('icon'),
            'reply_to': url_for('auth.post_secure_sesd_route', _external=True),
            'url': url_for('auth.get_paper_route', url=coursify(course_id, course.get('question')),
                           _external=True)
        })
    return respond_back(SUCCESS, data)


@auth.route('/<username>/<repo>{ext}'.format(ext=EXT))
@login_required
def initial_request_route(username, repo):
    course_owner = db.session.query(User).filter_by(username=username).first()
    if course_owner is None or course_owner.role < User.ADMINISTRATOR:
        return error_response('User does not exists or repository name is invalid')
    for repository in course_owner.repositories:
        if repository.repo_name == repo:
            return jsonify({'status': SUCCESS, 'url': urlify(course_owner, repository, 60 * 60 * 2), 'detail': 'Success'})
    return error_response('Invalid repository name')


@main.route('/get_routes')
def main_route():
    endpoints = {
        'login_to': url_for('main.login_route', _external=True),
        'add_user': url_for('main.signup_route', _external=True),
        'add_repository': url_for('auth.add_repository_route', _external=True),
        'add_course': url_for('auth.admin_add_course_route', _external=True),
        'get_repositories': url_for('auth.get_repositories_route', _external=True),
        'get_courses': url_for('auth.get_courses_route', _external=True),
        'upload_image': url_for('auth.upload_image_route', _external=True),
        'upload_file': url_for('auth.upload_file_route', _external=True),
        'delete_repo': url_for('auth.delete_repository_route', _external=True),
        'delete_course': url_for('auth.delete_course_route', _external=True),
        'edit_course': url_for('auth.edit_course_route', _external=True),
        'list_partakers': url_for('auth.list_partakers_route', _external=True),
        'delete_score' : url_for('auth.delete_exam_info_route', _external=True)
    }
    return jsonify({'status': SUCCESS, 'endpoints': endpoints})


@auth.route('/get_endpoints')
def get_endpoint_route():
    endpoints = { 'result': url_for('auth.get_result_route', _external=True ),
                  'ranking': url_for('auth.most_ranked_courses_route', _external=True)}
    return success_response(endpoints)


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


@auth.route('/')
def auth_route():
    return invalid_url_error()


@auth.route('/raw/<token>')
@login_required
def raw_route(token):
    expires = request.args.get('expires', None)
    if expires is None:
        return invalid_url_error()
    data = get_data(expires, token)
    if data is None:
        return invalid_url_error()
    owner = db.session.query(User).filter_by(username=data.get('staff_number', None)).first()
    if owner is None:
        return invalid_url_error()
    repository = db.session.query(Repository).filter_by(owner_id=owner.id, repo_name=data.get('repo_name')).first()
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
                                                      Course.repo_id == repository.id).all()
    return jsonify_courses(owner, list_of_courses, date_range_from, date_range_to)


@main.app_errorhandler(404)
def error_404(e):
    return invalid_url_error()


@auth.app_errorhandler(413)
def request_entity_too_large(e):
    return error_response('Request entity is too large')


@main.app_errorhandler(500)
def interval_server_error(e):
    return error_response('An internal server error occured')


@auth.route('/get_paper')
@login_required
def get_paper_route():
    data = get_data(60*60, request.args.get('url', None))
    if data is None:
        return invalid_url_error()
    fileid = data.get('id')
    random_number = randint(1, 300000)  # just a random number.
    return redirect(url_for('auth.get_question_route', file_id=fileid, path_generator=str(random_number), _external=True))


@auth.route('/get_question')
@login_required
def get_question_route():
    file_id = request.args.get('file_id', None)
    if request.args.get('path_generator') is None:
        return error_response('Invalid request')
    if file_id is None:
        return invalid_url_error()
    course = db.session.query(Course).filter_by(id=file_id).first()
    if course is None:
        return invalid_url_error()
    return send_file(course.quiz_filename)


# student exam solution data( sesd )
@auth.route('/p-sesd', methods=['POST'])
@login_required
def post_secure_sesd_route():
    try:
        data = request.get_json()
        course_token = data.get('course_id', None)
        date_taken = data.get('date_taken', None)
        answer_pair = data.get('answers')
        owner = data.get('owner')
        course_id = Course.get_course_id(course_token,EXPIRY_INTERVAL)
        if not all( (course_id, date_taken, answer_pair, owner, ) ):
            return error_response('One of the primary arguments are missing')
        repo_owner = db.session.query(User).filter_by(username=owner).first()
        if course_id is None or repo_owner is None:
            return respond_back(ERROR,'This course does not exist')
        course_taken = db.session.query(ExamTaken).filter_by(course_id=course_id,
                                participant_id=current_user.id).first()
        if course_taken is not None:
            return error_response('You have already taken this examination')
        # needed to verify JSON object's correctness for the answer
        answer_object = MyJSONObjectWriter()
        json.dump(answer_pair, answer_object, skipkeys=True, indent=2, separators=(',', ': '))
        other_data = answer_object.get_buffer()
        
        solution_data = { 'user_id': current_user.id, 'owner_id': repo_owner.id,
                        'course_id': course_id, 'data': other_data, 
                        'date_taken': date_taken }

        submit_paper_for_marking(current_user.email, json.dumps(solution_data))
        return success_response('OK')
    except BadRequest:
        return error_response('No data was specified')


@main.route('/user_login', methods=['POST'])
def login_route():
    try:
        data = request.get_json()
        if data is None:
            return respond_back( ERROR, 'Invalid request sent' )
        username = data.get('username', None)
        password = data.get('password', None)

        student = db.session.query(User).filter_by(username=username).first()
        if student is None:
            return jsonify({'status': ERROR, 'detail': 'Invalid login detail'})
        if not student.verify_password(password):
            return jsonify({'status': ERROR, 'detail': 'Invalid username or password'})
        login_user(student, False)
        return jsonify({'status': SUCCESS, 'detail': current_user.fullname,
            'dp_link': current_user.display_picture,
            'endpoints': url_for('auth.get_endpoint_route', _external=True) })
    except BadRequest:
        return error_response('Invalid login request received.')


@main.route('/signup', methods=['POST'])
def signup_route():
    try:
        data = request.get_json()
        if data is None:
            return error_response('Invalid request sent')
        name = data.get('full_name', None)
        address = data.get('address', None)
        email = data.get('email')
        username = data.get('username')
        phone_number = data.get('phone')
        password = data.get('password')
        
        if not all( ( name,address,email,username,password, ) ):
            return respond_back(ERROR,'Missing data member')
        if data_cache.sismember('tuq:usernames',username):
            return error_response('The username has been registered')
        if data_cache.sismember('tuq:emails',email):
            return respond_back(ERROR,'The email address has been registered')
        if phone_number is not None and len(phone_number) != 0 and data_cache.sismember('tuq:phones',phone_number):
            return error_response('The mobile number has been registered')
        user = User(username=username, fullname=name, email=email,alias=username,password=password,
                    address=address,role=User.NORMAL_USER,display_picture=DEFAULT_DISPLAY_PICTURE,
                    phone_number=phone_number,is_active_premium=False, date_of_registration=str(datetime.utcnow()))
        try:
            db.session.add(user)
            db.session.commit()
        except InvalidRequestError as invalid_request_err:
            print invalid_request_err
            return error_response('User detail already exist')
        data_cache.sadd('tuq:emails',email)
        data_cache.sadd('tuq:usernames',username)
        if phone_number is not None:
            data_cache.sadd('tuq:phones',phone_number)
        
        send_confirmation_message(email, user.id, name)
        return respond_back(SUCCESS,'A confirmation message has been sent to your email')
    except Exception as e:
        print e
        return error_response('Unable to process signup request')


@main.route('/confirm', methods=['GET', 'POST'])
def confirm_user_route():
    if request.method == 'GET':
        token = request.args.get('token')
        if not User.confirm_user_with_token(EXPIRY_INTERVAL, token=token):
            return error_response('You have either been confirmed or used an invalid/expired link.')
        else:
            return error_response('Your account has been successfully confirmed')
    else:
        try:
            data = request.get_json()
            if data is None:
                return error_response('Invalid data')
            email_address = data.get('email')
            if email_address is None:
                return error_response('No email address was specified')
            if not data_cache.sismember('tuq:emails', email_address):
                return error_response('Email address is not registered')
            user = db.session.query(User).filter_by(email=email_address).first()
            if user is None:
                return error_response('No user with that email exist')
            send_confirmation_message(user.email, user.id, user.fullname)
            return success_response('A confirmation mail has been sent to your address')
        except Exception as exc:
            print 'Error: {}'.format(str(exc))
            return error_response('Unable to process request')


@auth.route('/get_results', methods=['GET'])
@login_required
def get_result_route():
    all_results = db.session.query(ExamTaken).filter_by(participant_id=current_user.id).all()
    data = []
    for result in all_results:
        course_info = data_cache.hget(well_known_courses, result.course_id)
        course_info_obj = None
        if course_info is None:
            course_info = db.session.query(Course).filter_by(id=result.course_id).first()
            if course_info is None:  # still none?
                print 'We have an issue with {}'.format(result.course_id)
                continue
            #  otherwise cache it
            course_cache = {'name': course_info.name, 'id': course_info.id,
                            'owner': course_info.lecturer_in_charge,
                            'question': course_info.quiz_filename,
                            'code': course_info.code, 'solution': course_info.solution_filename}
            data_cache.hset(well_known_courses,result.course_id, json.dumps(course_cache))
            course_info_obj = course_cache  # no need to recheck the data_cache, just use the data
        if course_info_obj is None:  # if it has not been loaded yet, use the data obtained
            course_info_obj = json.loads(course_info)
        data.append({'name': course_info_obj['name'], 'score': result.score, 'date': result.date_taken,
                     'total': result.total_score,
                     'code': course_info_obj['code'], 'owner': course_info_obj['owner']})
    return success_response(data)


@auth.route('/add_repository', methods=['POST'])
@login_required
@administrator_required
def add_repository_route():
    try:
        data = request.get_json()
        if data is None:
            return error_response('Invalid data')
        repository_name = data.get('repository_name')
        if repository_name is None or len(repository_name) == 0:
            return error_response('Invalid repository name supplied')
        for repo in current_user.repositories:
            if repo.repo_name == repository_name:
                return error_response('Repository with that name already exist in your account')
        repository = Repository(repo_name=repository_name)
        current_user.repositories.append(repository)

        safe_makedir(UPLOAD_DIR, current_user.username, repository_name)

        db.session.add(repository)
        db.session.add(current_user)
        db.session.commit()
        url = '{url}{username}/{repo}{ext}'.format(url=url_for('auth.auth_route', _external=True),
                username=current_user.username,repo=repository.repo_name, ext=EXT)
        return success_response(url)
    except BadRequest:
        return error_response('Bad request')
    except Exception as e:
        print e
        return error_response('Unable to add repository, check the data and try again')


def update_course(data, user, database_handle):
    if data is None:
        raise ValueError('Invalid data')
    course_name = data.get('name')
    course_code = data.get('course_code')
    personnel_in_charge = data.get('administrator_name')
    hearing_date = data.get('date_to_be_held')
    duration_in_minutes = data.get('duration')
    question = data.get('question')
    approach = data.get('approach')
    randomize_question = data.get('randomize')
    expires = data.get('expires_on')
    solution = data.get('answers')
    icon_location = data.get('icon')

    departments = data.get('departments')
    repository_name = data.get('repository_name')
    if course_code is None or course_name is None or personnel_in_charge is None \
            or hearing_date is None or duration_in_minutes is None or departments is None \
            or question is None or randomize_question is None or approach is None \
            or solution is None or icon_location is None:
        raise ValueError('Missing arguments')
    repositories = user.repositories
    repository_to_use = None
    for repo in repositories:
        if repo.repo_name == repository_name:
            repository_to_use = repo
            break

    if repository_to_use is None:
        raise ValueError('Repository does not exist')
    course_to_use = None
    for course in repository_to_use.courses:
        if course_code == course.code:
            course_to_use = course
            break
    if course_to_use is None:
        raise ValueError('Course does not exist')

    department_list = []
    try:
        for department_name in departments:
            department_list.append(Department(name=department_name))
    except AttributeError:
        raise ValueError('Expects a valid data in the departments')

    try:
        with open(course_to_use.quiz_filename, mode='wt') as out:
            json.dump(question, out, sort_keys=True, indent=4, separators=(',', ': '))
        with open(course_to_use.solution_filename, mode='wt') as out:
            json.dump(solution, out, indent=True, separators=(',', ': '))
    except ValueError:
        raise ValueError( 'Invalid JSON Document for question')
    course_to_use.name = course_name
    course_to_use.lecturer_in_charge = personnel_in_charge
    course_to_use.answers_approach = approach
    course_to_use.expires_on = expires
    course_to_use.date_to_be_held = date_from_string( hearing_date )
    course_to_use.duration_in_minutes = int(duration_in_minutes)
    course_to_use.departments = department_list
    course_to_use.randomize_questions = randomize_question
    course_to_use.logo_location = icon_location
    
    repository_to_use.courses.append(course_to_use)
    database_handle.session.add(course_to_use)
    db.session.commit()
    course_cache = {'name': course_to_use.name, 'id': course_to_use.id,
                    'owner': course_to_use.lecturer_in_charge, 'icon': icon_location,
                    'code': course_to_use.code, 'solution': course_to_use.solution_filename,
                    'question': course_to_use.quiz_filename}
    data_cache.hset(well_known_courses, course_to_use.id, json.dumps(course_cache))


@auth.route('/admin_add_course', methods=['POST'])
@login_required
@administrator_required
def admin_add_course_route():
    try:
        data = request.get_json()
        if data is None:
            return error_response('Invalid data')
            
        print data

        course_name = data.get('name')
        course_code = data.get('course_code')
        personnel_in_charge = data.get('administrator_name')
        hearing_date = data.get('date_to_be_held')
        duration_in_minutes = data.get('duration')
        question = data.get('question')
        approach = data.get('approach')
        randomize_question = data.get('randomize')
        expires = data.get('expires_on')
        solution = data.get('answers')
        icon = data.get('icon')
        
        departments = data.get('departments')
        repository_name = data.get('repository_name')

        if course_code is None or course_name is None or personnel_in_charge is None\
                or hearing_date is None or duration_in_minutes is None or departments is None\
                or question is None or randomize_question is None or approach is None\
                or solution is None or icon is None:
            return error_response('Missing arguments')

        repositories = current_user.repositories
        repository_to_use = None
        for repo in repositories:
            if repo.repo_name == repository_name:
                repository_to_use = repo
                break

        if repository_to_use is None:
            return error_response('Repository does not exist')
        for course in repository_to_use.courses:
            if course_code == course.code:
                return error_response('Course with that code already exist')

        department_list = []
        try:
            for department_name in departments:
                if len(department_name.strip()) != 0:
                    department_list.append(Department(name=department_name))
        except AttributeError:
            return error_response('Expects a valid data in the departments')

        full_path, solution_fn = (None, None)
        try:
            filename = course_code.replace(' ', '_').replace('.', '_') + '.json'
            dir_path = safe_makedir(UPLOAD_DIR, current_user.username, repository_name)
            full_path = safe_join(dir_path, filename)
            solution_fn = safe_join(dir_path, 'solutions_'+ filename)

            with open(full_path, mode='wt') as out:
                json.dump(question, out, sort_keys=True, indent=4, separators=(',', ': '))
            with open( solution_fn, mode='wt') as out:
                json.dump(solution, out, indent=True, separators=(',', ': '))
        except ValueError:
            return error_response('Invalid JSON Document for question')
        course = Course(name=course_name, code=course_code, lecturer_in_charge=personnel_in_charge,
                        answers_approach=approach, expires_on=expires,
                        date_to_be_held=date_from_string(hearing_date), duration_in_minutes=int(duration_in_minutes),
                        departments=department_list, quiz_filename=full_path, solution_filename = solution_fn,
                        randomize_questions=randomize_question, logo_location=icon)

        repository_to_use.courses.append(course)

        db.session.add(course)
        db.session.add(repository_to_use)
        db.session.add(current_user)

        db.session.commit()
        course_cache = {'name': course.name, 'id': course.id, 'owner': course.lecturer_in_charge,
                        'code': course.code, 'solution': course.solution_filename,
                        'icon': course.logo_location,
                        'question': course.quiz_filename}
        data_cache.hset(well_known_courses, course.id, json.dumps(course_cache))
        return success_response('New course added successfully')
    except BadRequest:
        return error_response('Bad request')
    except Exception as e:
        print e
        return error_response('Could not add the course')


@auth.route('/edit_course', methods=['GET', 'POST'])
@login_required
@administrator_required
def edit_course_route():
    if request.method == 'GET':
        try:
            course_id = request.args.get('course_id')
            repository_name = request.args.get('repository_name')
            if course_id is None or len(course_id) < 1 or repository_name is None:
                return error_response('Missing request argument')
            repository = db.session.query(Repository).\
                filter_by(repo_name=repository_name,owner_id=current_user.id).first()
            if repository is None or repository.owner_id != current_user.id:
                return respond_back(ERROR,'Repository does not exist')
            course = db.session.query(Course).filter_by(id=long(course_id), repo_id=repository.id).first()
            if course is None:
                return error_response('No course under that name was found')
            departments = [ dept for dept in course.departments if len(dept.name.strip()) != 0]
            
            question_file = open(course.quiz_filename, 'r')
            answer_file = open(course.solution_filename, 'r')
            data = {'name': course.name, 'course_code': course.code,
                    'administrator_name': course.lecturer_in_charge,
                    'departments': departments, 'repository_name': repository_name,
                    'date_to_be_held': str(course.date_to_be_held), 'icon': course.logo_location,
                    'duration': course.duration_in_minutes, 'approach': course.answers_approach,
                    'randomize': course.randomize_questions, 'expires_on': str(course.expires_on),
                    'question': json.load(question_file), 'answers': json.load(answer_file)
                    }
            question_file.close()
            answer_file.close()
            return success_response(data)
        except Exception as exc:
            print 'Exception caught: {}\n'.format(str(exc))
            return error_response('Unable to get that information')
    else:
        try:
            update_course(request.get_json(), current_user, db)
            return success_response('Update performed successfully')
        except ValueError as value_error:
            return error_response(str(value_error))
        except Exception as exc:
            print exc
            return error_response('Unable to perform course update')


@auth.route('/get_repositories')
@login_required
@administrator_required
def get_repositories_route():
    repositories = [{'name': repository.repo_name,
                     'url': '{url}{username}/{repo}{ext}'.format(url=
                                                                 url_for('auth.auth_route', _external=True),
                                                                 username=current_user.username,
                                                                 repo=repository.repo_name, ext=EXT),
                     'courses': [[course.name, course.id] for course in repository.courses]} for repository in
                    current_user.repositories]
    return jsonify({'status': SUCCESS, 'repositories': repositories, 'detail': 'Successful'})


# todo: debug like no other
@auth.route('/most_ranked_courses')
@login_required
def most_ranked_courses_route():
    limit = request.args.get('limit')
    max_score, min_score = data_cache.zrange(all_course_ranks,-1,-1), 0
    max_score = long(max_score[0]) if len(max_score)>0 else 0

    limit_start = 0
    try:
        limit_stop = int(limit) if (limit is not None and int(limit) < 40) else 20
    except ValueError:
        limit_stop = 20
    try:
        most_ranked = data_cache.zrevrangebyscore(all_course_ranks, max_score, min_score, limit_start, limit_stop)
        most_ranked = map(lambda data: long(data), most_ranked)
    except ValueError:
        return error_response('Unable to service request')
    courses = data_cache.hmget(well_known_courses, most_ranked)
    return rank_courses_result(courses)


@auth.route('/delete_exam_info')
@administrator_required
def delete_exam_info_route():
    try:
        reference_id = request.args.get('ref_id')
        if not reference_id:
            return error_response('Invalid reference id')
        reference_id = long(reference_id[3:])
        exam = db.session.query(ExamTaken).filter_by(id=reference_id).first()
        if not exam:
            return error_response('No course with that reference ID exists')
        db.session.delete(exam)
        db.session.commit()
        return success_response('Successful')
    except ValueError as val_error:
        print 'ValueError: {}\n'.format(str(val_error))
        return error_response('Invalid reference number')
    except Exception as exc:
        print 'GeneralException: {}\n'.format(str(exc))
        return error_response('Unable to process requests')


@auth.route('/list_partakers')
@login_required
@administrator_required
def list_partakers_route():
    try:
        repo_name = request.args.get('repository')
        course_id = long(request.args.get('course_id'))
        course = db.session.query(Course).filter_by(id=course_id).first()
        if course is None:
            return error_response('Course not found')
        # next three lines are strictly to confirm the user is really the owner of the course
        repo = db.session.query(Repository).filter_by(owner_id=current_user.id, repo_name=repo_name).first()
        if repo is None or course.repo_id != repo.id:
            return success_response('Unable to locate the course')
        all_courses = db.session.query(ExamTaken, User).filter(ExamTaken.course_owner==current_user.id,
                        ExamTaken.course_id == course_id).\
                        filter(ExamTaken.participant_id==User.id).order_by(ExamTaken.date_taken).all()
        result_data = []
        for each_course_tuple in all_courses:
            exam, user = each_course_tuple[0], each_course_tuple[1]
            result_data.append( {'fullname': user.fullname, 'username': user.username, 
                                 'score': exam.score, 'total': exam.total_score,
                                 'date_time': exam.date_taken, 'reference_id': '0x4'+str(exam.id) })
        return success_response(result_data)
    except ValueError as val_error:
        print 'ValueError: {}\n'.format(str(val_error))
        return error_response('Invalid parameters')
    except Exception as exc:
        print 'GeneralException: {}\n'.format(str(exc))
        return error_response('Unable to process requests')


@auth.route('/get_courses_from_repo')
@login_required
@administrator_required
def get_courses_route():
    try:
        repository_name = request.args.get('repository')
        if repository_name is None:
            return error_response('Invalid repository name')
        repository = db.session.query(Repository).filter_by(user_id=current_user.id, repo_name=repository_name).first()
        if repository is None:
            return error_response('Nothing found')
        return jsonify({'status': SUCCESS, 'courses': list_courses_data(repository.courses)})
    except BadRequest:
        return error_response('Bad request')


def upload(upload_object, request_object, username, data):
    # file_index: just a custom header to ensure the upload comes from an accredited client
    file_index = request_object.headers.get('FileIndex')
    if file_index is None:
        return error_response('Data does not originate from accredited source')
    if data in request_object.files:
        repository_name = request_object.args.get('repository')
        if repository_name is None or len(str(repository_name)) < 1:
            return error_response('Invalid repository name')
        try:
            sub_dir = '{parent_dir}/{sub}'.format(parent_dir=username, sub=repository_name)
            filename = upload_object.save(request_object.files[data], folder=sub_dir)
            url = upload_object.url(filename)
            url = url.replace('http', 'https', 1) if url.startswith('http') else url
            return jsonify({'status': SUCCESS, 'index': file_index, 'url': url})
        except UploadNotAllowed:
            return error_response('Upload type not allowed')
    return error_response('Invalid data')


@auth.route('/upload_image', methods=['POST'])
@login_required
@administrator_required
def upload_image_route():
    photo_object = premium_photos if current_user.is_active_premium else public_photos
    return upload( photo_object, request, current_user.username, 'photo')


@auth.route('/upload_raw_file', methods=['POST'])
@login_required
@administrator_required
def upload_file_route():
    raw_file_object = premium_raw_files if current_user.is_active_premium else public_raw_files
    return upload(raw_file_object, request, current_user.username, 'raw')


@auth.route('/delete_repository', methods=['POST'])
@login_required
@administrator_required
def delete_repository_route():
    json_data = request.get_json()
    if json_data is None:
        return respond_back(ERROR,'Invalid request data')
    repository_name = json_data.get( 'repository_name' )
    if repository_name is None or len(repository_name) == 0:
        return error_response('A valid repository name must be specified')
    try:
        for repository in current_user.repositories:
            if repository_name == repository.repo_name:
                db.session.delete(repository)
                db.session.commit()
                data_cache.rpush(deleted_repo_keys, current_user.username + '^^' + repository_name)
                return success_response('Removed successfully')
        return error_response('No such repository found for user')
    except Exception as exc:
        print exc
        return error_response('Unable to process request')


@auth.route('/delete_course', methods=['POST'])
@login_required
@administrator_required
def delete_course_route():
    json_data = request.get_json()
    if json_data is None:
        return error_response('Invalid request data')
    repository_name = json_data.get( 'repository_name') # repository under which the course can be found
    try:
        course_id = json_data.get('course_id')
        if course_id is None:
            return error_response('A valid course ID must be specified')
        course_id = long(course_id)
        repository = db.session.query(Repository).filter_by(owner_id=current_user.id, repo_name=repository_name).first()
        course = db.session.query(Course).filter_by(id=course_id, repo_id=repository.id).first()
        if course is None:
            return error_response('Cannot find courses with that name')
        course_id = course.id
        db.session.delete(course)
        db.session.commit()
        data_cache.hdel(well_known_courses, course_id)
        data_cache.rpush(deleted_course_keys, course_id)
        return success_response('Course removed successfully')
    except Exception as e:
        print e
        return error_response('Unable to delete course')


@auth.before_request
def before_auth_request():
    if request.headers.get('from') not in known_clients:
        return '<html><title>Client</title><body><h1>Invalid address</h1></body></html>'
    if not current_user.is_authenticated:
        return error_response('Not logged in')
    if not current_user.confirmed:
        return error_response('Account has not been confirmed yet')


@main.before_request
def before_main_request():
    if request.headers.get('from') not in known_clients:
        confirm = str(request.url_rule).startswith('/tuq/confirm')
        if not confirm:
            return '<html><title>Client</title><body><h1>Invalid address</h1></body></html>'

# ======================================The Web=======================================================

@web.route('/admin_signup.html', methods=['GET', 'POST'])
def admin_signup_route():
    links = Links()
    links.tuq_on_pc = url_for('web.tuq_on_pc_route',_external=True)
    links.admin_reg = url_for('web.admin_signup_route',_external=True)
    links.index_url = url_for('web.index_page_route',_external=True)
    form = AdminRequestForm()
    if form.validate_on_submit():
        submission_info = {'username': form.username.data, 'fullname': form.full_name.data,
                           'address': form.address.data, 'email': form.email.data,
                           'nationality': form.nationality.data, 'alias': form.display_name.data,
                           'mobile': form.phone_number.data, 'password': form.password.data }
        json_writer = MyJSONObjectWriter()
        json.dump(submission_info,json_writer, skipkeys=True, indent=2, separators=(',', ': '))
        data_string = json_writer.get_buffer()

        data_cache.hset('tuq:admin_requests', form.username.data, data_string)
        session['name']=form.full_name.data
        return redirect(url_for('web.submission_made_route', _external=True))
    else:
        return render_template('admin_register.html', form=form, links=links)


@web.route('/submission',methods=['GET'])
def submission_made_route():
    fullname = session.get('name', None)
    if fullname is None:
        return redirect(url_for('web.index_page_route',_external=True))
    session.pop('name')
    message = 'Thank you for using Tuq services, {}'.format(fullname)
    links = Links()
    links.tuq_on_pc = url_for('web.tuq_on_pc_route',_external=True)
    links.admin_reg = url_for('web.admin_signup_route',_external=True)
    links.index_url = url_for('web.index_page_route',_external=True)
    return render_template('submission.html', links=links, message=message)


@web.route('/')
def index_page_route():
    links = Links()
    links.tuq_on_pc = url_for('web.tuq_on_pc_route',_external=True)
    links.admin_reg = url_for('web.admin_signup_route',_external=True)
    links.index_url = url_for('web.index_page_route',_external=True)
    return render_template('index.html', links=links)


@web.route('/tuq_on_pc.html')
def tuq_on_pc_route():
    get_route_link = url_for('main.main_route', _external=True)
    links = Links()
    links.tuq_on_pc = url_for('web.tuq_on_pc_route',_external=True)
    links.admin_reg = url_for('web.admin_signup_route',_external=True)
    links.index_url = url_for('web.index_page_route',_external=True)
    return render_template('tuq_on_pc.html', main_link=get_route_link, links=links)
