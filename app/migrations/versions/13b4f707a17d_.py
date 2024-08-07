"""empty message

Revision ID: 13b4f707a17d
Revises: 80b166d06692
Create Date: 2024-05-30 04:55:56.475136

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '13b4f707a17d'
down_revision = '80b166d06692'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('http_check',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('url')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('http_check')
    # ### end Alembic commands ###
