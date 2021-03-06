"""Added total_score to ExamsTaken

Revision ID: 49783ae83566
Revises: 6723848870f0
Create Date: 2017-11-24 15:02:39.633000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '49783ae83566'
down_revision = '6723848870f0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('courses', 'randomize_questions',
               existing_type=mysql.TINYINT(display_width=1),
               type_=sa.Boolean(),
               existing_nullable=False)
    op.add_column('exams_taken', sa.Column('total_score', sa.Integer(), nullable=False))
    op.alter_column('users', 'is_active_premium',
               existing_type=mysql.TINYINT(display_width=1),
               type_=sa.Boolean(),
               existing_nullable=True)
    op.alter_column('users', 'is_confirmed',
               existing_type=mysql.TINYINT(display_width=1),
               type_=sa.Boolean(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'is_confirmed',
               existing_type=sa.Boolean(),
               type_=mysql.TINYINT(display_width=1),
               existing_nullable=True)
    op.alter_column('users', 'is_active_premium',
               existing_type=sa.Boolean(),
               type_=mysql.TINYINT(display_width=1),
               existing_nullable=True)
    op.drop_column('exams_taken', 'total_score')
    op.alter_column('courses', 'randomize_questions',
               existing_type=sa.Boolean(),
               type_=mysql.TINYINT(display_width=1),
               existing_nullable=False)
    # ### end Alembic commands ###
