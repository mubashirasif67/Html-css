"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'donor', 'employee', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create employees table
    op.create_table('employees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('cnic', sa.String(length=15), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('father_name', sa.String(length=100), nullable=False),
        sa.Column('grade', sa.Enum('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', name='employeegrade'), nullable=False),
        sa.Column('designation', sa.String(length=100), nullable=True),
        sa.Column('mobile', sa.String(length=15), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('family_key', sa.String(length=10), nullable=True),
        sa.Column('family_size', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('is_eligible', sa.Boolean(), nullable=True),
        sa.Column('eligibility_score', sa.Float(), nullable=True),
        sa.Column('fraud_flag', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employees_cnic'), 'employees', ['cnic'], unique=True)
    op.create_index(op.f('ix_employees_family_key'), 'employees', ['family_key'], unique=False)
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)

    # Create donations table
    op.create_table('donations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('donor_id', sa.Integer(), nullable=False),
        sa.Column('donor_name', sa.String(length=100), nullable=False),
        sa.Column('donor_email', sa.String(length=100), nullable=True),
        sa.Column('donor_cnic', sa.String(length=15), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('donation_type', sa.Enum('zakat', 'sadaqah', 'general', name='donationtype'), nullable=False),
        sa.Column('receipt_image_path', sa.String(length=255), nullable=True),
        sa.Column('detected_amount', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.Column('transaction_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['donor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_donations_id'), 'donations', ['id'], unique=False)
    op.create_index(op.f('ix_donations_transaction_hash'), 'donations', ['transaction_hash'], unique=False)

    # Create distribution_runs table
    op.create_table('distribution_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('run_date', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('total_beneficiaries', sa.Integer(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_distribution_runs_id'), 'distribution_runs', ['id'], unique=False)

    # Create distributions table
    op.create_table('distributions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('pickup_slot', sa.String(length=50), nullable=True),
        sa.Column('notification_sent', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['distribution_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_distributions_id'), 'distributions', ['id'], unique=False)

    # Create feedback table
    op.create_table('feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column('sentiment', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)


def downgrade():
    op.drop_table('feedback')
    op.drop_table('distributions')
    op.drop_table('distribution_runs')
    op.drop_table('donations')
    op.drop_table('employees')
    op.drop_table('users')