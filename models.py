from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # 'admin' or 'employee'
    telegram_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = db.relationship('Employee', backref='user', uselist=False, cascade='all, delete-orphan')
    actions = db.relationship('Action', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'telegram_id': self.telegram_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Employee(db.Model):
    """Employee model"""
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    
    # Task tracking
    tasks_today = db.Column(db.Integer, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')
    
    # Salary management
    base_salary = db.Column(db.Float, default=0.0)
    current_salary = db.Column(db.Float, default=0.0)
    total_bonuses = db.Column(db.Float, default=0.0)
    total_deductions = db.Column(db.Float, default=0.0)
    salary_currency = db.Column(db.String(10), default='UZS')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # The relationship 'user' is already defined in the User model with backref='employee'.
    # This line is redundant if 'user' is already defined in User with backref='employee'.
    # If 'employee_profile' is intended as a separate backref, it should be handled carefully.
    # For now, I'll assume the existing 'user' relationship in User is sufficient and remove this line
    # to avoid potential conflicts or duplicate relationship definitions.
    # user = db.relationship('User', backref='employee_profile') 
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'position': self.position,
            'department': self.department,
            'tasks_today': self.tasks_today,
            'tasks_completed': self.tasks_completed,
            'status': self.status,
            'base_salary': self.base_salary,
            'current_salary': self.current_salary,
            'total_bonuses': self.total_bonuses,
            'total_deductions': self.total_deductions,
            'salary_currency': self.salary_currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'email': self.user.email if self.user else None
        }


class Action(db.Model):
    """Action/Log model for tracking activities"""
    __tablename__ = 'actions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action_type': self.action_type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_email': self.user.email if self.user else None
        }


class Subscription(db.Model):
    """Subscription model for monetization"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100))
    plan_type = db.Column(db.String(20), default='free')  # free, pro, business
    employee_limit = db.Column(db.Integer, default=3)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'plan_type': self.plan_type,
            'employee_limit': self.employee_limit,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active
        }

class SalaryTransaction(db.Model):
    """Salary transaction model for tracking salary changes"""
    __tablename__ = 'salary_transactions'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # bonus, deduction, adjustment, base_change
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(200))
    previous_salary = db.Column(db.Float)
    new_salary = db.Column(db.Float)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    employee = db.relationship('Employee', backref='salary_transactions')
    creator = db.relationship('User', backref='salary_actions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'reason': self.reason,
            'previous_salary': self.previous_salary,
            'new_salary': self.new_salary,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
