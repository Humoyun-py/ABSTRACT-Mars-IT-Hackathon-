"""
Database initialization script
Run this to create/reset the database with default admin account
"""

from app import app, db
from models import User, Employee, Subscription, SalaryTransaction
from datetime import date

with app.app_context():
    # Drop all tables and recreate
    print("🗑️  Dropping all tables...")
    db.drop_all()
    
    print("📦 Creating tables...")
    db.create_all()
    
    # Create default admin
    print("👤 Creating default admin account...")
    admin = User(
        email='admin@platform.com',
        role='admin'
    )
    admin.set_password('admin123')
    db.session.add(admin)
    
    # Create test employee
    print("👤 Creating test employee account...")
    employee_user = User(
        email='test@example.com',
        phone='+998901234567',
        role='employee'
    )
    employee_user.set_password('test123')
    db.session.add(employee_user)
    db.session.flush()
    
    # Create employee record with salary
    employee = Employee(
        user_id=employee_user.id,
        full_name='Test Xodim',
        position='Dasturchi',
        department='IT',
        base_salary=5000000.0,
        current_salary=5000000.0,
        salary_currency='UZS'
    )
    db.session.add(employee)
    
    # Create default subscription
    print("💰 Creating default subscription...")
    subscription = Subscription(
        company_name='Default Company',
        plan_type='free',
        employee_limit=3,
        start_date=date.today(),
        is_active=True
    )
    db.session.add(subscription)
    
    # Commit all changes
    db.session.commit()
    
    print("\n✅ Database initialized successfully!")
    print("\n📋 Default accounts:")
    print("   Admin: admin@platform.com / admin123")
    print("   Employee: test@example.com / test123")
    print("\n🚀 You can now run: python app.py")
