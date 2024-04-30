"""empty message

Revision ID: fd2ea4b980d6
Revises: 812444c88b9e
Create Date: 2024-04-30 01:27:26.247459

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd2ea4b980d6'
down_revision = '812444c88b9e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('inventory_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('date_updated', sa.DateTime(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('inventory_config', schema=None) as batch_op:
        batch_op.drop_column('date_updated')

    # ### end Alembic commands ###