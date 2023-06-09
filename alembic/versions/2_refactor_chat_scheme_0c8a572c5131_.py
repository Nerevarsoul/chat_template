"""empty message

Revision ID: 0c8a572c5131
Revises: 9c10d536a11c
Create Date: 2023-04-29 07:40:31.605651

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0c8a572c5131"
down_revision = "9c10d536a11c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "chats",
        sa.Column(
            "state",
            sa.Enum("ACTIVE", "FOR_FAVORITE", "ARCHIVE", "FAVORITE", "DELETED", name="chatstate"),
            nullable=False,
        ),
    )
    op.add_column("chats", sa.Column("time_created", sa.DateTime(), nullable=False))
    op.add_column("chats", sa.Column("time_updated", sa.DateTime(), nullable=True))
    op.alter_column("chats_relationships", "unread_counter", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column("chats_relationships", "is_pinned", existing_type=sa.BOOLEAN(), nullable=False)
    op.alter_column(
        "chats_relationships",
        "user_role",
        existing_type=postgresql.ENUM("CREATOR", "ADMIN", "USER", "ONLY_FOR_DATA", name="chatuserrole"),
        nullable=False,
    )
    op.drop_column("chats_relationships", "is_admin")
    op.alter_column("users", "is_blocked", existing_type=sa.BOOLEAN(), nullable=False)
    op.drop_index("ix_users_uid", table_name="users")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index("ix_users_uid", "users", ["uid"], unique=False)
    op.alter_column("users", "is_blocked", existing_type=sa.BOOLEAN(), nullable=True)
    op.add_column("chats_relationships", sa.Column("is_admin", sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.alter_column(
        "chats_relationships",
        "user_role",
        existing_type=postgresql.ENUM("CREATOR", "ADMIN", "USER", "ONLY_FOR_DATA", name="chatuserrole"),
        nullable=True,
    )
    op.alter_column("chats_relationships", "is_pinned", existing_type=sa.BOOLEAN(), nullable=True)
    op.alter_column("chats_relationships", "unread_counter", existing_type=sa.INTEGER(), nullable=True)
    op.drop_column("chats", "time_updated")
    op.drop_column("chats", "time_created")
    op.drop_column("chats", "state")
    # ### end Alembic commands ###
