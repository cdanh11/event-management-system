"""Initial Evently schema: frozen snapshot, independent of runtime models."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Snapshot cố định: migration không phụ thuộc app.models của phiên bản sau.
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('avatar_url', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_table('events',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('organizer_id', sa.String(length=36), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('location', sa.String(length=300), nullable=False),
    sa.Column('start_time', sa.DateTime(), nullable=False),
    sa.Column('end_time', sa.DateTime(), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.Column('registered_count', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('category', sa.String(length=80), nullable=False),
    sa.Column('banner_url', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['organizer_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_organizer_id'), 'events', ['organizer_id'], unique=False)
    op.create_index(op.f('ix_events_status'), 'events', ['status'], unique=False)
    op.create_table('refresh_tokens',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_table('registrations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('attendee_id', sa.String(length=36), nullable=False),
    sa.Column('registered_at', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.ForeignKeyConstraint(['attendee_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id', 'attendee_id', name='uq_event_attendee')
    )
    op.create_index(op.f('ix_registrations_attendee_id'), 'registrations', ['attendee_id'], unique=False)
    op.create_index(op.f('ix_registrations_event_id'), 'registrations', ['event_id'], unique=False)
    op.create_table('staff_event_assignments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('staff_id', sa.String(length=36), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['staff_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('staff_id', 'event_id', name='uq_staff_event')
    )
    op.create_index(op.f('ix_staff_event_assignments_event_id'), 'staff_event_assignments', ['event_id'], unique=False)
    op.create_index(op.f('ix_staff_event_assignments_staff_id'), 'staff_event_assignments', ['staff_id'], unique=False)
    op.create_table('tickets',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('registration_id', sa.String(length=36), nullable=False),
    sa.Column('ticket_code', sa.String(length=32), nullable=False),
    sa.Column('qr_value', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('issued_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['registration_id'], ['registrations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tickets_registration_id'), 'tickets', ['registration_id'], unique=True)
    op.create_index(op.f('ix_tickets_ticket_code'), 'tickets', ['ticket_code'], unique=True)
    op.create_table('checkins',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('ticket_id', sa.String(length=36), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('attendee_id', sa.String(length=36), nullable=False),
    sa.Column('checked_in_by', sa.String(length=36), nullable=False),
    sa.Column('checked_in_at', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.ForeignKeyConstraint(['attendee_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['checked_in_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_checkins_attendee_id'), 'checkins', ['attendee_id'], unique=False)
    op.create_index(op.f('ix_checkins_event_id'), 'checkins', ['event_id'], unique=False)
    op.create_index(op.f('ix_checkins_ticket_id'), 'checkins', ['ticket_id'], unique=True)



def downgrade():
    for table in ["checkins", "tickets", "registrations", "staff_event_assignments", "refresh_tokens", "events", "users"]:
        op.drop_table(table)
