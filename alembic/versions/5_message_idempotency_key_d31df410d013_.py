"""empty message

Revision ID: d31df410d013
Revises: cab491b47f97
Create Date: 2023-07-09 08:43:43.642647

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d31df410d013"
down_revision = "cab491b47f97"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("messages", sa.Column("client_id", sa.UUID(), nullable=False))
    op.create_unique_constraint(None, "messages", ["client_id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("messages_client_id_key", table_name="messages")
    op.drop_column("messages", "client_id")
    # ### end Alembic commands ###
