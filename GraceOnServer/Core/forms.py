from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, ValidationError, SelectField, IntegerField, Label
from wtforms.validators import DataRequired, Email, Length, Regexp, EqualTo, Optional, InputRequired
from flask_login import current_user
from resources import data_cache


class AdminRequestForm( FlaskForm ):
    full_name = StringField('Full name', validators=[ DataRequired(), InputRequired(), Length(1, 24)])
    address = StringField('Address', validators=[InputRequired(), DataRequired(), Length(10, 512)])
    username = StringField('Username', validators=[DataRequired(), InputRequired(), Length(5, 64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(5, 64)])
    nationality = StringField('Nationality', validators= [InputRequired(), DataRequired()])
    display_name = StringField( 'Alias', validators=[Length(1, 64), Optional(),
                                                             Regexp('^[a-zA-Z_][A-Za-z0-9_]*$', 0,
                                                                    'Display name must start with an alphabet, '
                                                                    'followed by one or more alphanumeric characters')])
    phone_number = StringField('Phone number', validators=[DataRequired(), Length(10, 20)])
    password = PasswordField('Password', validators=[ DataRequired(), EqualTo('password2', message='Password must match'),
                                                         Length( 8, 96 ), InputRequired() ] )
    password2 = PasswordField('Repeat password', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_email(self, field):
        if data_cache.sismember('tuq:emails',field.data):
            raise ValidationError('Email address has already been registered')
    
    def validate_username(self, field):
        if data_cache.sismember('tuq:usernames',field.data):
            raise ValidationError('Username already registered')

    def validate_phone_number(self, field):
        if data_cache.sismember('tuq:phones',field.data):
            raise ValidationError('Mobile number already registered')
