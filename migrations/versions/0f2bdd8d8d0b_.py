"""empty message

Revision ID: 0f2bdd8d8d0b
Revises: 890d9af9f050
Create Date: 2017-12-01 05:39:05.383000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0f2bdd8d8d0b'
down_revision = '890d9af9f050'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('courses', 'randomize_questions',
               existing_type=mysql.TINYINT(display_width=1),
               type_=sa.Boolean(),
               existing_nullable=False)
    op.alter_column('exams_taken', 'participant_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
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
    op.alter_column('exams_taken', 'participant_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
    op.alter_column('courses', 'randomize_questions',
               existing_type=sa.Boolean(),
               type_=mysql.TINYINT(display_width=1),
               existing_nullable=False)
    # ### end Alembic commands ###
