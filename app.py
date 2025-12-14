from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from config import Config
from models import db, User, Employee, Action, Subscription, SalaryTransaction
from datetime import datetime, date
import os

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    
    # Create default admin if not exists
    admin = User.query.filter_by(email='admin@platform.com').first()
    if not admin:
        admin = User(
            email='admin@platform.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create default subscription
        subscription = Subscription(
            company_name='Default Company',
            plan_type='free',
            employee_limit=3,
            start_date=date.today(),
            is_active=True
        )
        db.session.add(subscription)
        db.session.commit()
        print("✅ Default admin created: admin@platform.com / admin123")

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('employee_dashboard'))
    return render_template('login.html')

@app.route('/login')
def login():
    """Login page"""
    return render_template('login.html')

@app.route('/register')
def register():
    """Register page"""
    return render_template('register.html')

@app.route('/employee/dashboard')
@login_required
def employee_dashboard():
    """Employee dashboard"""
    if current_user.role != 'employee':
        return redirect(url_for('admin_dashboard'))
    
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    from datetime import datetime
    today = datetime.now().strftime('%d %B %Y')
    return render_template('employee_dashboard.html', employee=employee, today=today)

@app.route('/employee/tasks')
@login_required
def employee_tasks():
    """Employee tasks page"""
    if current_user.role != 'employee':
        return redirect(url_for('admin_dashboard'))
    
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    return render_template('employee/tasks.html', employee=employee)

@app.route('/employee/profile')
@login_required
def employee_profile():
    """Employee profile page"""
    if current_user.role != 'employee':
        return redirect(url_for('admin_dashboard'))
    
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    return render_template('employee/profile.html', employee=employee)

@app.route('/employee/calendar')
@login_required
def employee_calendar():
    """Employee calendar page"""
    if current_user.role != 'employee':
        return redirect(url_for('admin_dashboard'))
    
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    return render_template('employee/calendar.html', employee=employee)

@app.route('/employee/messages')
@login_required
def employee_messages():
    """Employee messages page"""
    if current_user.role != 'employee':
        return redirect(url_for('admin_dashboard'))
    
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    return render_template('employee/messages.html', employee=employee)

@app.route('/employee/settings')
@login_required
def employee_settings():
    """Employee settings page"""
    if current_user.role != 'employee':
        return redirect(url_for('admin_dashboard'))
    
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    return render_template('employee/settings.html', employee=employee)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if current_user.role != 'admin':
        return redirect(url_for('employee_dashboard'))
    
    # Get statistics
    total_employees = Employee.query.filter_by(status='active').count()
    total_users = User.query.count()
    recent_actions = Action.query.order_by(Action.timestamp.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_employees=total_employees,
                         total_users=total_users,
                         recent_actions=recent_actions)

@app.route('/admin/employees')
@login_required
def admin_employees():
    """Admin employee management page"""
    if current_user.role != 'admin':
        return redirect(url_for('employee_dashboard'))
    
    employees = Employee.query.all()
    subscription = Subscription.query.filter_by(is_active=True).first()
    
    return render_template('admin/employees.html',
                         employees=employees,
                         subscription=subscription)

@app.route('/admin/statistics')
@login_required
def admin_statistics():
    """Admin statistics page"""
    if current_user.role != 'admin':
        return redirect(url_for('employee_dashboard'))
    
    return render_template('admin/statistics.html')

@app.route('/admin/bot')
@login_required
def admin_bot():
    """Admin bot control page"""
    if current_user.role != 'admin':
        return redirect(url_for('employee_dashboard'))
    
    return render_template('admin/bot_control.html')

@app.route('/admin/logs')
@login_required
def admin_logs():
    """Admin logs page"""
    if current_user.role != 'admin':
        return redirect(url_for('employee_dashboard'))
    
    actions = Action.query.order_by(Action.timestamp.desc()).all()
    return render_template('admin/logs.html', actions=actions)

@app.route('/admin/salary')
@login_required
def admin_salary():
    """Admin salary management page"""
    if current_user.role != 'admin':
        return redirect(url_for('employee_dashboard'))
    
    employees = Employee.query.all()
    return render_template('admin/salary.html', employees=employees)

# ==================== API ENDPOINTS ====================

# Authentication
@app.route('/api/login', methods=['POST'])
def api_login():
    """Login API endpoint"""
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email va parol kerak'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Email yoki parol noto\'g\'ri'}), 401
    
    login_user(user, remember=True)
    
    # Log action
    action = Action(
        user_id=user.id,
        action_type='login',
        description=f'{user.email} tizimga kirdi'
    )
    db.session.add(action)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'redirect': '/admin/dashboard' if user.role == 'admin' else '/employee/dashboard'
    })

@app.route('/api/register', methods=['POST'])
def api_register():
    """Register API endpoint"""
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data or 'full_name' not in data:
        return jsonify({'error': 'To\'liq ma\'lumot talab qilinadi'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'error': 'Bu email allaqachon ro\'yxatdan o\'tgan'}), 400
    
    # Check subscription limit (default free plan)
    subscription = Subscription.query.filter_by(is_active=True).first()
    current_count = Employee.query.filter_by(status='active').count()
    
    if subscription and current_count >= subscription.employee_limit:
        return jsonify({
            'error': f'Bepul rejada limit ({subscription.employee_limit}) to\'ldi. Admin bilan bog\'laning!',
            'limit_reached': True
        }), 403
    
    # Create user (as employee role)
    user = User(
        email=data['email'],
        phone=data.get('phone'),
        role='employee'
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.flush()
    
    # Create employee record
    employee = Employee(
        user_id=user.id,
        full_name=data['full_name'],
        position=data.get('position'),
        department=data.get('department')
    )
    db.session.add(employee)
    
    # Log action
    action = Action(
        user_id=user.id,
        action_type='user_registered',
        description=f'Yangi foydalanuvchi ro\'yxatdan o\'tdi: {data["full_name"]}'
    )
    db.session.add(action)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Muvaffaqiyatli ro\'yxatdan o\'tdingiz!'
    }), 201

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    """Logout API endpoint"""
    logout_user()
    return jsonify({'success': True})

@app.route('/api/me')
@login_required
def api_me():
    """Get current user info"""
    return jsonify(current_user.to_dict())

# Employee Management
@app.route('/api/employees', methods=['GET'])
@login_required
def api_get_employees():
    """Get all employees"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    employees = Employee.query.all()
    return jsonify([emp.to_dict() for emp in employees])

@app.route('/api/employees', methods=['POST'])
@login_required
def api_create_employee():
    """Create new employee"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    data = request.get_json()
    
    # Check subscription limit
    subscription = Subscription.query.filter_by(is_active=True).first()
    current_count = Employee.query.filter_by(status='active').count()
    
    if subscription and current_count >= subscription.employee_limit:
        return jsonify({
            'error': f'Xodimlar limiti ({subscription.employee_limit}) to\'ldi. Rejangizni yangilang!',
            'limit_reached': True,
            'current_plan': subscription.plan_type
        }), 403
    
    # Create user
    user = User(
        email=data['email'],
        phone=data.get('phone'),
        role='employee'
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.flush()
    
    # Create employee
    employee = Employee(
        user_id=user.id,
        full_name=data['full_name'],
        position=data.get('position'),
        department=data.get('department')
    )
    db.session.add(employee)
    
    # Log action
    action = Action(
        user_id=current_user.id,
        action_type='employee_created',
        description=f'Yangi xodim qo\'shildi: {data["full_name"]}'
    )
    db.session.add(action)
    
    db.session.commit()
    
    return jsonify({'success': True, 'employee': employee.to_dict()}), 201

@app.route('/api/employees/<int:id>', methods=['PUT'])
@login_required
def api_update_employee(id):
    """Update employee"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    employee = Employee.query.get_or_404(id)
    data = request.get_json()
    
    employee.full_name = data.get('full_name', employee.full_name)
    employee.position = data.get('position', employee.position)
    employee.department = data.get('department', employee.department)
    employee.status = data.get('status', employee.status)
    
    # Log action
    action = Action(
        user_id=current_user.id,
        action_type='employee_updated',
        description=f'Xodim yangilandi: {employee.full_name}'
    )
    db.session.add(action)
    
    db.session.commit()
    
    return jsonify({'success': True, 'employee': employee.to_dict()})

@app.route('/api/employees/<int:id>', methods=['DELETE'])
@login_required
def api_delete_employee(id):
    """Delete employee"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    employee = Employee.query.get_or_404(id)
    user = User.query.get(employee.user_id)
    
    name = employee.full_name
    
    db.session.delete(employee)
    if user:
        db.session.delete(user)
    
    # Log action
    action = Action(
        user_id=current_user.id,
        action_type='employee_deleted',
        description=f'Xodim o\'chirildi: {name}'
    )
    db.session.add(action)
    
    db.session.commit()
    
    return jsonify({'success': True})

# Statistics
@app.route('/api/stats')
@login_required
def api_stats():
    """Get platform statistics"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    stats = {
        'total_employees': Employee.query.filter_by(status='active').count(),
        'total_users': User.query.count(),
        'total_tasks_today': db.session.query(db.func.sum(Employee.tasks_today)).scalar() or 0,
        'total_tasks_completed': db.session.query(db.func.sum(Employee.tasks_completed)).scalar() or 0,
        'recent_actions': [action.to_dict() for action in Action.query.order_by(Action.timestamp.desc()).limit(10).all()]
    }
    
    return jsonify(stats)

@app.route('/api/actions')
@login_required
def api_actions():
    """Get activity logs"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    actions = Action.query.order_by(Action.timestamp.desc()).limit(100).all()
    return jsonify([action.to_dict() for action in actions])

# Telegram Bot (placeholder endpoints)
@app.route('/api/bot/send', methods=['POST'])
@login_required
def api_bot_send():
    """Send message via Telegram bot"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    data = request.get_json()
    # TODO: Implement Telegram bot sending
    
    return jsonify({'success': True, 'message': 'Xabar yuborildi'})

@app.route('/api/bot/notify', methods=['POST'])
@login_required
def api_bot_notify():
    """Notify employees via Telegram"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    data = request.get_json()
    # TODO: Implement Telegram notification
    
    return jsonify({'success': True, 'message': 'Bildirishnoma yuborildi'})

@app.route('/api/bot/stats')
@login_required
def api_bot_stats():
    """Get bot statistics"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    # TODO: Implement bot statistics
    return jsonify({
        'total_messages': 0,
        'active_users': 0
    })

# Salary Management APIs
@app.route('/api/employees/<int:id>/salary', methods=['GET'])
@login_required
def api_get_employee_salary(id):
    """Get employee salary details"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    employee = Employee.query.get_or_404(id)
    transactions = SalaryTransaction.query.filter_by(employee_id=id).order_by(SalaryTransaction.created_at.desc()).limit(10).all()
    
    return jsonify({
        'employee': employee.to_dict(),
        'recent_transactions': [t.to_dict() for t in transactions]
    })

@app.route('/api/employees/<int:id>/salary/bonus', methods=['POST'])
@login_required
def api_add_bonus(id):
    """Add bonus to employee salary"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    employee = Employee.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'amount' not in data:
        return jsonify({'error': 'Summa kiritilmagan'}), 400
    
    amount = float(data['amount'])
    reason = data.get('reason', 'Premia')
    
    # Update salary
    previous_salary = employee.current_salary
    employee.current_salary += amount
    employee.total_bonuses += amount
    
    # Create transaction
    transaction = SalaryTransaction(
        employee_id=employee.id,
        transaction_type='bonus',
        amount=amount,
        reason=reason,
        previous_salary=previous_salary,
        new_salary=employee.current_salary,
        created_by=current_user.id
    )
    db.session.add(transaction)
    
    # Log action
    action = Action(
        user_id=current_user.id,
        action_type='salary_bonus',
        description=f'{employee.full_name}ga {amount:,.0f} {employee.salary_currency} premia qo\'shildi'
    )
    db.session.add(action)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'employee': employee.to_dict(),
        'transaction': transaction.to_dict()
    })

@app.route('/api/employees/<int:id>/salary/deduction', methods=['POST'])
@login_required
def api_deduct_salary(id):
    """Deduct from employee salary"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    employee = Employee.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'amount' not in data:
        return jsonify({'error': 'Summa kiritilmagan'}), 400
    
    amount = float(data['amount'])
    reason = data.get('reason', 'Ajratish')
    
    # Update salary
    previous_salary = employee.current_salary
    employee.current_salary -= amount
    employee.total_deductions += amount
    
    # Create transaction
    transaction = SalaryTransaction(
        employee_id=employee.id,
        transaction_type='deduction',
        amount=amount,
        reason=reason,
        previous_salary=previous_salary,
        new_salary=employee.current_salary,
        created_by=current_user.id
    )
    db.session.add(transaction)
    
    # Log action
    action = Action(
        user_id=current_user.id,
        action_type='salary_deduction',
        description=f'{employee.full_name}dan {amount:,.0f} {employee.salary_currency} ajratildi'
    )
    db.session.add(action)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'employee': employee.to_dict(),
        'transaction': transaction.to_dict()
    })

@app.route('/api/employees/<int:id>/salary/base', methods=['PUT'])
@login_required
def api_update_base_salary(id):
    """Update employee base salary"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    employee = Employee.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'amount' not in data:
        return jsonify({'error': 'Summa kiritilmagan'}), 400
    
    new_base = float(data['amount'])
    reason = data.get('reason', 'Asosiy maosh o\'zgarishi')
    
    # Update salaries
    previous_salary = employee.current_salary
    salary_diff = new_base - employee.base_salary
    
    employee.base_salary = new_base
    employee.current_salary += salary_diff
    
    # Create transaction
    transaction = SalaryTransaction(
        employee_id=employee.id,
        transaction_type='base_change',
        amount=new_base,
        reason=reason,
        previous_salary=previous_salary,
        new_salary=employee.current_salary,
        created_by=current_user.id
    )
    db.session.add(transaction)
    
    # Log action
    action = Action(
        user_id=current_user.id,
        action_type='salary_base_update',
        description=f'{employee.full_name}ning asosiy maoshi {new_base:,.0f} {employee.salary_currency}ga o\'zgartirildi'
    )
    db.session.add(action)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'employee': employee.to_dict(),
        'transaction': transaction.to_dict()
    })

@app.route('/api/employees/<int:id>/salary/history', methods=['GET'])
@login_required
def api_salary_history(id):
    """Get salary transaction history"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    transactions = SalaryTransaction.query.filter_by(employee_id=id).order_by(SalaryTransaction.created_at.desc()).all()
    
    return jsonify([t.to_dict() for t in transactions])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
