#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2017 Joshua <ogunyinkajoshua@gmail.com>


from flask import Blueprint, jsonify, request, redirect, send_file, safe_join, render_template, flash
from werkzeug.exceptions import BadRequest
from datetime import date
from sqlalchemy.exc import InvalidRequestError
from models import db, User, Course, ExamTaken, Department, Repository, DEFAULT_DISPLAY_PICTURE
from resources import urlify, get_data, respond_back, jsonify_courses, administrator_required
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

public_photos = UploadSet('photos', IMAGES, default_dest=lambda app: os.environ.get('GENERAL_UPLOAD_DIRECTORY'))
public_raw_files = UploadSet('rawFiles', RAW_FILES, default_dest=lambda app: os.environ.get('GENERAL_UPLOAD_DIRECTORY'))
premium_photos = UploadSet( 'photos', IMAGES, default_dest=lambda app: os.environ.get('PREMIUM_UPLOAD_DIRECTORY'))
premium_raw_files = UploadSet( 'rawFiles', RAW_FILES, default_dest=lambda app: os.environ.get('PREMIUM_UPLOAD_DIRECTORY') )

internal_url_for = url_for

def invalid_url_error():
    return respond_back(ERROR, 'Invalid URL specified')


def safe_makedir(parent_path, path, paths=''):
    user_directory = os.path.join(parent_path, safe_join(path, paths))
    if not os.path.exists(user_directory):
        os.makedirs(user_directory)
    return user_directory


@auth.route('/<username>/<repo>{ext}'.format(ext=EXT))
@login_required
def initial_request_route(username, repo):
    course_owner = db.session.query(User).filter_by(username=username).first()
    if course_owner is None or course_owner.role < User.ADMINISTRATOR:
        return respond_back(ERROR, 'User does not exists or repository name is invalid')
    for repository in course_owner.repositories:
        if repository.repo_name == repo:
            return jsonify({'status': SUCCESS, 'url': urlify(course_owner, repository, 60 * 60 * 2), 'detail': 'Success'})
    return respond_back(ERROR, 'Invalid repository name')


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
        'edit_course': url_for('auth.edit_course_route', _external=True)
    }
    return jsonify({'status': SUCCESS, 'endpoints': endpoints})


@auth.route('/get_endpoints')
def get_endpoint_route():
    endpoints = { 'result': url_for( 'auth.get_result_route', _external=True ) }
    return respond_back(SUCCESS, endpoints)


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
    return respond_back(ERROR, 'Request entity is too large')


@main.app_errorhandler(500)
def interval_server_error(e):
    return respond_back(ERROR, 'An internal server error occured')


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
        return respond_back(ERROR, 'Invalid request')
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
            return respond_back(ERROR, 'One of the primary arguments are missing')
        repo_owner = db.session.query(User).filter_by(username=owner).first()
        if course_id is None or repo_owner is None:
            return respond_back(ERROR,'This course does not exist')
        course_taken = db.session.query(ExamTaken).filter_by(course_id=course_id,
                                participant_id=current_user.id).first()
        if course_taken is not None:
            return respond_back(ERROR, 'You have already taken this examination')
        # needed to verify JSON object's correctness for the answer
        answer_object = MyJSONObjectWriter()
        json.dump(answer_pair, answer_object, skipkeys=True, indent=2, separators=(',', ': '))
        other_data = answer_object.get_buffer()
        
        solution_data = { 'user_id': current_user.id, 'owner_id': repo_owner.id,
                        'course_id': course_id, 'data': other_data, 
                        'date_taken': date_taken }

        submit_paper_for_marking(current_user.email, json.dumps(solution_data))
        return respond_back(SUCCESS, 'OK')
    except BadRequest:
        return respond_back(ERROR, 'No data was specified')


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
        return respond_back(ERROR, 'Invalid login request received.')


@main.route('/admin_signup', methods=['GET', 'POST'])
def admin_signup_route():
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
        flash('Thank you for using Tuq services, {}'.format(form.full_name.data))
        return redirect(url_for('main.submission_made_route', _external=True))
    else:
        return render_template('admin_register.html', form=form)


@main.route('/submission',methods=['GET'])
def submission_made_route():
    return render_template('submission.html')


@main.route('/signup', methods=['POST', 'GET'])
def signup_route():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if data is None:
                return respond_back(ERROR, 'Invalid request sent')
            name = data.get('full_name', None)
            address = data.get('address', None)
            email = data.get('email')
            username = data.get('username')
            phone_number = data.get('phone')
            password = data.get('password')
            
            if not all( ( name,address,email,username,phone_number,password, ) ):
                return respond_back(ERROR,'Missing data member')
            if data_cache.sismember('tuq:usernames',username):
                return respond_back(ERROR, 'The username has been registered')
            if data_cache.sismember('tuq:emails',email):
                return respond_back(ERROR,'The email address has been registered')
            if data_cache.sismember('tuq:phones',phone_number):
                return respond_back(ERROR, 'The mobile number has been registered')
            user = User(username=username, fullname=name, email=email,alias=username,password=password,
                        address=address,role=User.NORMAL_USER,display_picture=DEFAULT_DISPLAY_PICTURE,
                        phone_number=phone_number,is_active_premium=False)
            try:
                db.session.add(user)
                db.session.commit()
            except InvalidRequestError as invalid_request_err:
                print invalid_request_err
                return respond_back(ERROR, 'User detail already exist')
            data_cache.sadd('tuq:emails',email)
            data_cache.sadd('tuq:usernames',username)
            data_cache.sadd('tuq:phones',phone_number)
            
            send_confirmation_message(email, user.id, name)
            return respond_back(SUCCESS,'A confirmation message has been sent to your email')
        except Exception as e:
            print e
            return respond_back(ERROR, 'Unable to process signup request')
    else:
        return respond_back(SUCCESS, 'Not yet implemented')


@main.route('/confirm', methods=['GET'])
def confirm_user_route():
    token = request.args.get('token')
    if not User.confirm_user_with_token(EXPIRY_INTERVAL, token=token):
        return respond_back(ERROR, 'You have either been confirmed or used an invalid/expired link.')
    else:
        return respond_back(ERROR, 'Your account has been successfully confirmed')


@auth.route('/get_results', methods=['GET'])
@login_required
def get_result_route():
    all_results = db.session.query(ExamTaken).filter_by(id=current_user.id).all()
    data = []
    for result in all_results:
        course_info = data_cache.hget(well_known_courses, result.course_id)
        course_info_obj = None
        if course_info is None:
            course_info = db.session.query(Course).filter_by(id=result.course_id).first()
            if course_info is None:  # still none?
                continue
            #  otherwise cache it
            course_cache = {'name': course_info.name, 'id': course_info.id,
                            'owner': course_info.lecturer_in_charge,
                            'code': course_info.code, 'solution': course_info.solution_filename}
            data_cache.hset(well_known_courses,result.course_id, json.dumps(course_cache))
            course_info_obj = course_cache  # no need to recheck the data_cache, just use the data
        if course_info_obj is None:  # if it has not been loaded yet, use the data obtained
            course_info_obj = json.loads(course_info)
        data.append({'name': course_info_obj['name'], 'score': result.score, 'date': result.date_taken,
                     'code': course_info_obj['code'], 'owner': course_info_obj['owner']})
    return respond_back(SUCCESS, data)


@auth.route('/add_repository', methods=['POST'])
@login_required
@administrator_required
def add_repository_route():
    try:
        data = request.get_json()
        if data is None:
            return respond_back(ERROR, 'Invalid data')
        repository_name = data.get('repository_name')
        if repository_name is None or len(repository_name) == 0:
            return respond_back(ERROR, 'Invalid repository name supplied')
        for repo in current_user.repositories:
            if repo.repo_name == repository_name:
                return respond_back(ERROR, 'Repository with that name already exist in your account')
        repository = Repository(repo_name=repository_name)
        current_user.repositories.append(repository)

        safe_makedir(UPLOAD_DIR, current_user.username, repository_name)

        db.session.add(repository)
        db.session.add(current_user)
        db.session.commit()
        return respond_back(SUCCESS, 'Successful')
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

        departments = data.get('departments')
        repository_name = data.get('repository_name')

        if course_code is None or course_name is None or personnel_in_charge is None\
                or hearing_date is None or duration_in_minutes is None or departments is None\
                or question is None or randomize_question is None or approach is None\
                or solution is None:
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
                department_list.append(Department(name=department_name))
        except AttributeError:
            return respond_back(ERROR, 'Expects a valid data in the departments')

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
            return respond_back(ERROR, 'Invalid JSON Document for question')
        course = Course(name=course_name, code=course_code, lecturer_in_charge=personnel_in_charge,
                        answers_approach=approach, expires_on=expires,
                        date_to_be_held=date_from_string(hearing_date), duration_in_minutes=int(duration_in_minutes),
                        departments=department_list, quiz_filename=full_path, solution_filename = solution_fn,
                        randomize_questions=randomize_question)

        repository_to_use.courses.append(course)

        db.session.add(course)
        db.session.add(repository_to_use)
        db.session.add(current_user)

        db.session.commit()
        course_cache = { 'name': course.name, 'id': course.id, 'owner': course.lecturer_in_charge,
                        'code': course.code, 'solution': course.solution_filename }
        is_set = data_cache.hset(well_known_courses,course.id, json.dumps(course_cache))
        print 'New course set: {}'.format( is_set )
        return respond_back(SUCCESS, 'New course added successfully')
    except BadRequest:
        return respond_back(ERROR, 'Bad request')
    except Exception as e:
        print e
        return respond_back(ERROR, 'Could not add the course')


@auth.route('/get_repositories')
@login_required
@administrator_required
def get_repositories_route():
    repositories = [{'name': repository.repo_name,
                     'url': '{url}{username}/{repo}{ext}'.format(url=
                                                                 url_for('auth.auth_route', _external=True),
                                                                 username=current_user.username,
                                                                 repo=repository.repo_name, ext=EXT),
                     'courses': [course.name for course in repository.courses]} for repository in
                    current_user.repositories]
    return jsonify({'status': 1, 'repositories': repositories, 'detail': 'Successful'})


@auth.route('/get_courses_from_repo')
@login_required
@administrator_required
def get_courses_route():
    try:
        repository_name = request.args.get('repository')
        if repository_name is None:
            return respond_back(ERROR, 'Invalid repository name')
        repository = db.session.query(Repository).filter_by(user_id=current_user.id, repo_name=repository_name).first()
        if repository is None:
            return respond_back(ERROR, 'Nothing found')
        return jsonify({'status': SUCCESS, 'courses': list_courses_data(repository.courses)})
    except BadRequest:
        return respond_back(ERROR, 'Bad request')


def upload(upload_object, request_object, username, data):
    # file_index: just a custom header to ensure the upload comes from an accredited client
    file_index = request_object.headers.get('FileIndex')
    if file_index is None:
        return respond_back(ERROR, 'Data does not originate from accredited source')
    if data in request_object.files:
        repository_name = request_object.args.get('repository')
        if repository_name is None or len(str(repository_name)) < 1:
            return respond_back(ERROR, 'Invalid repository name')
        try:
            sub_dir = '{parent_dir}/{sub}'.format(parent_dir=username, sub=repository_name)
            filename = upload_object.save(request_object.files[data], folder=sub_dir)
            url = upload_object.url(filename)
            return jsonify({'status': SUCCESS, 'index': file_index, 'url': url})
        except UploadNotAllowed:
            return respond_back(ERROR, 'Upload type not allowed')
    return respond_back(ERROR, 'Invalid data')


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
    if repository_name is None:
        return respond_back(ERROR, 'A repository name must be specified')
    for repo in current_user.repositories:
        if repository_name == repo.repo_name:
            db.session.delete(repo)
            db.session.commit()
            return respond_back(SUCCESS,'Removed successfully')
    return respond_back(ERROR, 'No such repository found for user')


@auth.route('/delete_course', methods=['POST'])
@login_required
@administrator_required
def delete_course_route():
    json_data = request.get_json()
    if json_data is None:
        return respond_back(ERROR, 'Invalid request data')
    repository_name = json_data.get( 'repository_name') # repository under which the course can be found
    course_name = json_data.get('course_name')
    if course_name is None:
        return respond_back(ERROR, 'A course name must be specified')
    repository = db.session.query( Repository ).filter_by( repo_name = repository_name,
                                                           user_id = current_user.id ).first()
    if repository is None:
        return respond_back(ERROR, 'Cannot find repository housing the course')
    course = db.session.query( Course ).filter_by( repo_id = repository.id, name = course_name ).first()
    if course is None:
        return respond_back(ERROR, 'Cannot find the course specified')
    db.session.remove(course)
    db.session.commit()
    data_cache.hdel(well_known_courses,course.id)
            
    return respond_back(SUCCESS, 'Course removed successfully')


# to-do: Fix edit courses
@auth.route('/edit_course', methods=['GET', 'POST'])
@login_required
@administrator_required
def edit_course_route():
    if request.method == 'GET':
        course_name = request.args.get( 'course_name' )
        repository_name = request.args.get( 'repository_name')
        if course_name is None or repository_name is None:
            return respond_back(ERROR, 'Missing request argument')
        
    else:
        return respond_back(SUCCESS, 'OK')


@auth.before_request
def before_auth_request():
    if not current_user.is_authenticated:
        return respond_back(ERROR, 'Not logged in')
    if not current_user.confirmed:
        return respond_back(ERROR, 'Account has not been confirmed yet')
