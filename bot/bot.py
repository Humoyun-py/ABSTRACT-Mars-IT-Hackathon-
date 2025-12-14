import os
import sqlite3
import json
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Bot token
BOT_TOKEN = "7549756529:AAGF1Qtsuk2ZVJemkjve2GkjMTmxSVItIPo"
ADMIN_IDS = [7782143104]
# Website URL
WEBSITE_URL = "http://127.0.0.1:5000/"  # Change this to your website URL
# Botni ishga tushirish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Database connection
def get_db():
    # Connect to the web app's database (assuming it's in the parent directory)
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'database.db')
    if not os.path.exists(db_path):
        # Fallback to root directory if instance folder not used
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database - Skipped as we use Web App's DB
def init_database():
    pass

# ... (States classes remain the same) ...

# Admin States
class AdminStates(StatesGroup):
    adding_employee = State()
    editing_employee = State()
    deleting_employee = State()
    adding_bonus = State()
    adding_penalty = State()
    adding_kpi = State()
    viewing_registrations = State()
    processing_registration = State()

# Helper functions...
def format_number(num):
    if num is None:
        return "0"
    return f"{float(num):,.0f}".replace(",", " ")

def clean_number(text):
    if text is None:
        return "0"
    cleaned = re.sub(r'[^\d.]', '', str(text))
    parts = cleaned.split('.')
    if len(parts) > 1:
        cleaned = parts[0] + '.' + ''.join(parts[1:])
    if cleaned == '' or cleaned == '.':
        return "0"
    return cleaned

def parse_salary(text):
    try:
        cleaned = clean_number(text)
        return float(cleaned)
    except (ValueError, TypeError):
        return 0

def get_current_month():
    return datetime.now().strftime('%Y-%m')

def get_employee_by_telegram_id(telegram_id):
    conn = get_db()
    c = conn.cursor()
    # Join Users and Employees tables
    query = """
        SELECT e.*, u.role, u.email, u.phone 
        FROM employees e
        JOIN users u ON e.user_id = u.id
        WHERE u.telegram_id = ?
    """
    c.execute(query, (str(telegram_id),))
    employee = c.fetchone()
    conn.close()
    
    if employee:
        emp_dict = dict(employee)
        # Adapt name/surname for bot compatibility
        full_name = emp_dict.get('full_name', '')
        parts = full_name.split(' ', 1)
        emp_dict['name'] = parts[0]
        emp_dict['surname'] = parts[1] if len(parts) > 1 else ''
        return emp_dict
    return None

def check_registration_status(telegram_id):
    """Check if user has registered (pending or accepted)"""
    conn = get_db()
    c = conn.cursor()
    # In web app, we check Users table for pending role or status
    # Assuming 'employee' role means active/accepted
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),))
    user = c.fetchone()
    
    if user:
        return {'status': 'active', 'name': 'User', 'surname': ''}
        
    conn.close()
    return None

def get_total_bonus(employee_id, month):
    conn = get_db()
    c = conn.cursor()
    # Using salary_transactions table from web app
    c.execute('''SELECT SUM(amount) as total FROM salary_transactions 
                 WHERE employee_id = ? 
                 AND transaction_type = 'bonus'
                 AND strftime('%Y-%m', created_at) = ?''',
              (employee_id, month))
    result = c.fetchone()['total'] or 0
    conn.close()
    return result

def get_total_penalty(employee_id, month):
    conn = get_db()
    c = conn.cursor()
    # Using salary_transactions table from web app
    c.execute('''SELECT SUM(amount) as total FROM salary_transactions 
                 WHERE employee_id = ? 
                 AND transaction_type = 'deduction'
                 AND strftime('%Y-%m', created_at) = ?''',
              (employee_id, month))
    result = c.fetchone()['total'] or 0
    conn.close()
    return result

# Keyboards with back button
def get_main_menu(telegram_id):
    if telegram_id in ADMIN_IDS:
        keyboard = [
            [InlineKeyboardButton(text="➕ Xodim qo'shish", callback_data="add_employee")],
            [InlineKeyboardButton(text="✏️ Xodimni tahrirlash", callback_data="edit_employee")],
            [InlineKeyboardButton(text="❌ Xodimni o'chirish", callback_data="delete_employee")],
            [InlineKeyboardButton(text="� Xodimlarni boshqarish", callback_data="manage_employees")],
            [InlineKeyboardButton(text="�💰 Bonus berish", callback_data="add_bonus")],
            [InlineKeyboardButton(text="⚠️ Jarima berish", callback_data="add_penalty")],
            [InlineKeyboardButton(text="📈 KPI qo'shish", callback_data="add_kpi")],
            [InlineKeyboardButton(text="📋 Ro'yxatdan o'tish so'rovlari", callback_data="view_registrations")],
            [InlineKeyboardButton(text="📊 Statistika", callback_data="stats")],
            [InlineKeyboardButton(text="🔄 Hisoblash", callback_data="calculate")],
            [InlineKeyboardButton(text="🌐 Veb-sayt", url=WEBSITE_URL)]
        ]
    else:
        employee = get_employee_by_telegram_id(telegram_id)
        if employee and employee.get('status') == 'active':
            # User is registered and APPROVED (active status)
            keyboard = [
                [InlineKeyboardButton(text="💰 Mening maoshim", callback_data="salary")],
                [InlineKeyboardButton(text="📈 Mening KPI'im", callback_data="kpi")],
                [InlineKeyboardButton(text="🎁 Bonuslarim", callback_data="bonus")],
                [InlineKeyboardButton(text="⚠️ Jarimalarim", callback_data="penalty")],
                [InlineKeyboardButton(text="📊 Hisobot", callback_data="report")],
                [InlineKeyboardButton(text="👤 Profilim", callback_data="profile")],
                [InlineKeyboardButton(text="🌐 Veb-sayt", url=WEBSITE_URL)]
            ]
        elif employee and employee.get('status') == 'pending':
            # User has registered but waiting for admin approval
            keyboard = [
                [InlineKeyboardButton(text="⏳ Ro'yxatdan o'tish kutilmoqda", callback_data="wait_registration")],
                [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")],
                [InlineKeyboardButton(text="🌐 Veb-sayt", url=WEBSITE_URL)]
            ]
        else:
            # User hasn't registered yet
            keyboard = [
                [InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", callback_data="register")],
                [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")],
                [InlineKeyboardButton(text="🌐 Veb-sayt", url=WEBSITE_URL)]
            ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_button():
    return [[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]]

def get_back_to_admin():
    return [[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin_menu")]]

# =============== COMMON HANDLERS ===============
@dp.message(CommandStart())
async def cmd_start(message: Message):
    telegram_id = message.from_user.id
    
    init_database()  # Ensure database exists
    
    # Admin uchun
    if telegram_id in ADMIN_IDS:
        await message.answer(
            "👨‍💼 **Admin paneliga xush kelibsiz!**\n"
            "Quyidagi menyudan kerakli amalni tanlang:",
            reply_markup=get_main_menu(telegram_id)
        )
    else:
        employee = get_employee_by_telegram_id(telegram_id)
        if employee:
            # User is fully registered and accepted
            await message.answer(
                f"👤 **Xush kelibsiz, {employee.get('name', 'Xodim')}!**\n"
                "Quyidagi menyudan kerakli ma'lumotni tanlang:",
                reply_markup=get_main_menu(telegram_id)
            )
        else:
            # Check if user has a pending registration
            reg_status = check_registration_status(telegram_id)
            if reg_status and reg_status['status'] == 'pending':
                # User has already registered, waiting for admin approval
                await message.answer(
                    "⏳ **Sizning ro'yxatdan o'tish so'rovingiz kutilmoqda!**\n\n"
                    "Administrator so'rovingizni ko'rib chiqadi va sizga javob beradi.\n"
                    "Iltimos, biroz sabr qiling...",
                    reply_markup=get_main_menu(telegram_id)
                )
            else:
                # User hasn't registered yet
                await message.answer(
                    "🤝 **Xush kelibsiz!**\n\n"
                    "Bu bot orqali siz o'zingizning maosh, bonus, jarima va KPI ma'lumotlaringizni ko'rishingiz mumkin.\n\n"
                    "📝 **Ro'yxatdan o'tish uchun** quyidagi tugmani bosing:",
                    reply_markup=get_main_menu(telegram_id)
                )

# =============== REGISTRATION HANDLERS ===============
# =============== REGISTRATION HANDLERS ===============
@dp.callback_query(lambda c: c.data == "clear_and_register")
async def clear_and_register(callback_query: types.CallbackQuery, state: FSMContext):
    """Clear user data and start fresh registration"""
    telegram_id = callback_query.from_user.id
    
    # Delete from employees table
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()
    
    # Start registration
    await state.set_state(UserStates.waiting_phone)
    await callback_query.message.edit_text(
        "📱 **Ro'yxatdan o'tish uchun avval kontaktingizni kiriting**\n\n"
        "Telefon raqamingizni kiriting:\n"
        "Misol: +998901234567 yoki 901234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.callback_query(lambda c: c.data == "wait_registration")
async def wait_registration(callback_query: types.CallbackQuery):
    """Show pending registration status"""
    telegram_id = callback_query.from_user.id
    reg_status = check_registration_status(telegram_id)
    
    if not reg_status:
        await callback_query.answer("❌ Ro'yxatdan o'tish ma'lumoti topilmadi!", show_alert=True)
        return
    
    reg_dict = dict(reg_status) if isinstance(reg_status, dict) else {
        'status': reg_status['status'],
        'name': getattr(reg_status, 'name', 'Noma\'lum'),
        'surname': getattr(reg_status, 'surname', '')
    }
    
    await callback_query.message.edit_text(
        "⏳ **Ro'yxatdan o'tish kutilmoqda**\n\n"
        "Sizning so'rovingiz administrator tomonidan ko'rib chiqilmoqda.\n"
        "Tasdiqlanganingizdan so'ng, siz botning barcha imkoniyatlarini ishlatishingiz mumkin bo'ladi.\n\n"
        "📋 Holatı: **Kutilmoqda** ⏳",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.callback_query(lambda c: c.data == "register")
async def start_registration(callback_query: types.CallbackQuery, state: FSMContext):
    # Check if user is already registered
    telegram_id = callback_query.from_user.id
    
    employee = get_employee_by_telegram_id(telegram_id)
    if employee:
        # User is already registered - clear/reset and ask if they want to change info
        keyboard = [
            [InlineKeyboardButton(text="✅ Keep current info", callback_data="back_to_main")],
            [InlineKeyboardButton(text="🔄 Update my information", callback_data="clear_and_register")],
        ]
        await callback_query.message.edit_text(
            f"👤 **You are already registered as:**\n\n"
            f"👤 Name: {employee.get('name', 'Unknown')}\n"
            f"👥 Surname: {employee.get('surname', 'Unknown')}\n"
            f"📱 Phone: {employee.get('phone', 'Not set')}\n"
            f"💼 Position: {employee.get('position', 'Not set')}\n"
            f"💰 Salary: {format_number(employee.get('base_salary', 0))} so'm\n\n"
            f"What would you like to do?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return
    
    reg_status = check_registration_status(telegram_id)
    if reg_status and reg_status['status'] == 'pending':
        await callback_query.answer("❌ Sizning so'rovingiz kutilmoqda! Iltimos, biroz sabr qiling.", show_alert=True)
        return
    
    # First, ask for contact/phone number
    await state.set_state(UserStates.waiting_phone)
    await callback_query.message.edit_text(
        "📱 **Ro'yxatdan o'tish uchun avval kontaktingizni kiriting**\n\n"
        "Telefon raqamingizni kiriting:\n"
        "Misol: +998901234567 yoki 901234567",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.message(UserStates.waiting_phone)
async def process_phone_first(message: Message, state: FSMContext):
    phone = message.text.strip()
    # Telefon raqamini tekshirish
    if not re.match(r'^(\+998|998|0)?[0-9]{9}$', phone.replace(" ", "")):
        await message.answer("❌ Noto'g'ri telefon raqami format! To'g'ri kiriting.")
        return
    
    # Save phone and show confirmation
    await state.update_data(phone=phone)
    
    text = f"📱 **Sizning kontaktingiz:**\n\n"
    text += f"📱 Telefon: {phone}\n\n"
    text += f"Bu raqam to'g'rimi?"
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Ha, to'g'ri", callback_data="confirm_phone")],
        [InlineKeyboardButton(text="❌ Yo'q, o'zgartirish", callback_data="edit_phone")]
    ]
    
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data == "edit_phone")
async def edit_phone(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_phone)
    await callback_query.message.edit_text(
        "📱 Telefon raqamingizni yana kiriting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.callback_query(lambda c: c.data == "confirm_phone")
async def confirm_phone(callback_query: types.CallbackQuery, state: FSMContext):
    # Phone confirmed, now start full registration
    await state.set_state(UserStates.waiting_name)
    await callback_query.message.edit_text(
        "📝 **Ro'yxatdan o'tish**\n\n"
        "Iltimos, ismingizni kiriting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.message(UserStates.waiting_name)
async def process_name(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("❌ Iltimos, to'g'ri ism kiriting (kamida 2 harf)")
        return
    
    await state.update_data(name=message.text.strip())
    await state.set_state(UserStates.waiting_surname)
    await message.answer(
        "Familiyangizni kiriting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.message(UserStates.waiting_surname)
async def process_surname(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("❌ Iltimos, to'g'ri familiya kiriting (kamida 2 harf)")
        return
    
    await state.update_data(surname=message.text.strip())
    await state.set_state(UserStates.waiting_position)
    await message.answer(
        "Lavozimingizni kiriting:\n"
        "Misol: Dasturchi, Menejer, Buxgalter",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.message(UserStates.waiting_position)
async def process_position(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("❌ Iltimos, lavozimingizni kiriting")
        return
    
    await state.update_data(position=message.text.strip())
    await state.set_state(UserStates.waiting_salary)
    await message.answer(
        "💵 **Iltimos, maosh haqidagi o'zingizning taxminingizni kiriting:**\n\n"
        "Siz qancha maosh olishni xoxlaysiz?\n"
        "**Format:** Har qanday formatda kiriting\n"
        "**Misollar:**\n"
        "• 5 000 000 so'm\n"
        "• $500\n"
        "• 3.5 million\n"
        "• 2500000\n\n"
        "Biz sizning taxminingizni admin ko'rib chiqadi va maosh belgilaydi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.message(UserStates.waiting_salary)
async def process_salary(message: Message, state: FSMContext):
    salary_text = message.text.strip()
    if not salary_text:
        await message.answer("❌ Iltimos, maosh taxminingizni kiriting")
        return
    
    # Maoshni raqamga aylantirish
    salary_amount = parse_salary(salary_text)
    
    if salary_amount <= 0:
        await message.answer("❌ Maosh noto'g'ri kiritildi. Iltimos, raqam kiriting")
        return
    
    user_data = await state.get_data()
    telegram_id = message.from_user.id
    
    # Save registration request
    conn = get_db()
    c = conn.cursor()
    
    # Check if user is already in employees table
    c.execute("SELECT id FROM employees WHERE telegram_id = ?", (telegram_id,))
    existing_employee = c.fetchone()
    
    # Check if user already has a pending registration request
    c.execute("SELECT id FROM registration_requests WHERE telegram_id = ? AND status = 'pending'", 
              (telegram_id,))
    existing_request = c.fetchone()
    
    if existing_request and not existing_employee:
        await message.answer("❌ Siz allaqachon ro'yxatdan o'tish so'rovi yuborgansiz. Iltimos, admin javobini kuting.")
        await state.clear()
        conn.close()
        return
    
    # Add user to users table (AUTH)
    if not existing_employee:
        try:
            # 1. Create User
            c.execute('''INSERT INTO users 
                         (email, password_hash, role, telegram_id, phone, created_at)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (f"{telegram_id}@platform.com", # Generated email
                       "pbkdf2:sha256:600000$...", # Hack: dummy hash or we need to generate real one. 
                       # For now let's set a placeholder that won't work for web login until they set a password
                       'employee',
                       str(telegram_id), 
                       user_data['phone'],
                       datetime.now()))
            
            user_id = c.lastrowid
            
            # 2. Create Employee Profile
            full_name = f"{user_data['name']} {user_data['surname']}"
            c.execute('''INSERT INTO employees 
                         (user_id, full_name, position, base_salary, status, tasks_today, tasks_completed)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (user_id,
                       full_name,
                       user_data['position'],
                       salary_amount,
                       'active', # Auto-activate for now or 'pending'
                       0, 0))
            
            conn.commit()
            
            await message.answer(
                f"✅ **Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!**\n\n"
                f"Siz tizimga qo'shildingiz.\n"
                f"Web-saytga kirish uchun vaqtinchalik login: `{telegram_id}@platform.com`",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=get_main_menu(telegram_id).inline_keyboard)
            )
            
        except Exception as e:
            print(f"Registration error: {e}")
            await message.answer("❌ Xatolik yuz berdi. Bu telefon raqam yoki ID allaqachon mavjud bo'lishi mumkin.")
    
    conn.close()
    await state.clear()

# =============== ADMIN REGISTRATION HANDLERS ===============
@dp.callback_query(lambda c: c.data == "view_registrations")
async def view_registrations(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM registration_requests WHERE status = 'pending' ORDER BY requested_at DESC")
    requests = c.fetchall()
    conn.close()
    
    if not requests:
        await callback_query.message.edit_text(
            "📭 **Hozircha yangi so'rovlar yo'q.**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
        )
        return
    
    # Birinchi so'rovni ko'rsatish
    request = dict(requests[0])
    
    text = f"📋 **Ro'yxatdan o'tish so'rovi (#{request['id']}):**\n\n"
    text += f"👤 Ism: {request['name']}\n"
    text += f"👥 Familiya: {request['surname']}\n"
    text += f"📱 Telefon: {request['phone']}\n"
    text += f"💼 Lavozim: {request['position']}\n"
    text += f"💰 Maosh taxmini: {format_number(request['salary_request'])} so'm\n"
    text += f"🆔 Telegram ID: {request['telegram_id']}\n"
    text += f"📅 So'rov sanasi: {request['requested_at'].split()[0] if request['requested_at'] else 'Noma\'lum'}\n\n"
    text += f"📊 Jami {len(requests)} ta yangi so'rov mavjud."
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_{request['id']}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{request['id']}")],
        [InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"next_reg_{request['id']}")],
        [InlineKeyboardButton(text="💵 Maosh belgilash", callback_data=f"setsalary_{request['id']}")],
        get_back_to_admin()[0]
    ]
    
    await state.update_data(current_request_id=request['id'], all_requests=requests)
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(lambda c: c.data.startswith("accept_"))
async def accept_registration(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    request_id = int(callback_query.data.split("_")[1])
    
    conn = get_db()
    c = conn.cursor()
    
    # Get request details
    c.execute("SELECT * FROM registration_requests WHERE id = ?", (request_id,))
    request = c.fetchone()
    
    if not request:
        await callback_query.answer("❌ So'rov topilmadi!", show_alert=True)
        conn.close()
        return
    
    request = dict(request)
    
    # Check if employee already exists in employees table
    c.execute("SELECT id, status FROM employees WHERE telegram_id = ?", (request['telegram_id'],))
    existing = c.fetchone()
    
    if existing:
        existing_dict = dict(existing)
        # User already registered, just update their status to active
        c.execute("UPDATE employees SET status = 'active' WHERE telegram_id = ?", 
                 (request['telegram_id'],))
        salary_msg = f"Maosh: {format_number(request['salary_request'])} so'm (specified)"
    else:
        # Add to employees with salary from request
        default_salary = float(request['salary_request']) * 0.9 if request['salary_request'] else 3000000
        
        c.execute('''INSERT INTO employees 
                     (name, surname, telegram_id, phone, position, base_salary, role, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (request['name'], request['surname'], request['telegram_id'], 
                   request['phone'], request['position'], default_salary, 
                   'employee', 'active'))
        
        employee_id = c.lastrowid
        
        # Create initial KPI record
        c.execute('''INSERT INTO kpis (employee_id, month, kpi)
                     VALUES (?, ?, ?)''',
                  (employee_id, get_current_month(), 100))
        
        salary_msg = f"Maosh: {format_number(default_salary)} so'm (90% of request)"
    
    # Update request status
    c.execute("UPDATE registration_requests SET status = 'accepted' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    
    # Notify user
    try:
        await bot.send_message(
            request['telegram_id'],
            f"🎉 **Tabriklaymiz!**\n\n"
            f"✅ Sizning ro'yxatdan o'tish so'rovingiz qabul qilindi!\n\n"
            f"📋 **Sizning ma'lumotlaringiz:**\n"
            f"👤 Ism: {request['name']} {request['surname']}\n"
            f"📱 Telefon: {request['phone']}\n"
            f"💼 Lavozim: {request['position']}\n"
            f"{salary_msg}\n\n"
            f"🎯 Endi siz o'zingizning maosh, bonus va KPI ma'lumotlaringizni ko'rishingiz mumkin.\n"
            f"Bosh menyuga qaytish uchun /start buyrug'ini bosing.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Boshlash", callback_data="start_employee")]
            ])
        )
    except Exception as e:
        print(f"Notification error: {e}")
    
    await callback_query.answer(f"✅ {request['name']} {request['surname']} qabul qilindi!", show_alert=True)
    
    # Show next request or go back
    await view_registrations(callback_query, state)

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_registration(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    request_id = int(callback_query.data.split("_")[1])
    
    conn = get_db()
    c = conn.cursor()
    
    # Get request details
    c.execute("SELECT * FROM registration_requests WHERE id = ?", (request_id,))
    request = c.fetchone()
    
    if not request:
        await callback_query.answer("❌ So'rov topilmadi!", show_alert=True)
        conn.close()
        return
    
    request = dict(request)
    
    # Update request status
    c.execute("UPDATE registration_requests SET status = 'rejected' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    
    # Notify user
    try:
        await bot.send_message(
            request['telegram_id'],
            f"❌ **Xabar:**\n\n"
            f"Sizning ro'yxatdan o'tish so'rovingiz rad etildi.\n"
            f"Iltimos, keyinroq yana urinib ko'ring yoki administrator bilan bog'laning."
        )
    except Exception as e:
        print(f"Notification error: {e}")
    
    await callback_query.answer(f"❌ {request['name']} {request['surname']} rad etildi!", show_alert=True)
    
    # Show next request or go back
    await view_registrations(callback_query, state)

@dp.callback_query(lambda c: c.data.startswith("setsalary_"))
async def set_salary_start(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    request_id = int(callback_query.data.split("_")[1])
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM registration_requests WHERE id = ?", (request_id,))
    request = c.fetchone()
    conn.close()
    
    if not request:
        await callback_query.answer("❌ So'rov topilmadi!", show_alert=True)
        return
    
    request = dict(request)
    await state.update_data(request_id=request_id, request=request)
    await state.set_state(AdminStates.processing_registration)
    
    await callback_query.message.edit_text(
        f"💰 **Maosh belgilash:**\n\n"
        f"👤 Xodim: {request['name']} {request['surname']}\n"
        f"💼 Lavozim: {request['position']}\n"
        f"📱 Telefon: {request['phone']}\n"
        f"💰 Taxminiy maosh: {format_number(request['salary_request'])} so'm\n\n"
        f"📝 **Yangi maoshni kiriting:**\n"
        f"Har qanday formatda kiriting (5 000 000, $500, 3.5 million, 2500000)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
    )

@dp.message(AdminStates.processing_registration)
async def set_salary_finish(message: Message, state: FSMContext):
    salary_text = message.text.strip()
    if not salary_text:
        await message.answer("❌ Iltimos, maosh kiriting")
        return
    
    # Maoshni raqamga aylantirish
    salary_amount = parse_salary(salary_text)
    
    if salary_amount <= 0:
        await message.answer("❌ Maosh noto'g'ri kiritildi. Iltimos, raqam kiriting")
        return
    
    state_data = await state.get_data()
    request_id = state_data.get('request_id')
    request = state_data.get('request')
    
    conn = get_db()
    c = conn.cursor()
    
    # Check if employee already exists
    c.execute("SELECT id FROM employees WHERE telegram_id = ?", (request['telegram_id'],))
    existing = c.fetchone()
    
    if existing:
        # Update existing employee's salary and status
        c.execute("UPDATE employees SET base_salary = ?, status = 'active' WHERE telegram_id = ?", 
                 (salary_amount, request['telegram_id']))
        status_msg = "Maosh yangilandi"
    else:
        # Add new employee
        c.execute('''INSERT INTO employees 
                     (name, surname, telegram_id, phone, position, base_salary, role, status)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (request['name'], request['surname'], request['telegram_id'], 
                   request['phone'], request['position'], salary_amount, 
                   'employee', 'active'))
        
        employee_id = c.lastrowid
        
        # Create initial KPI record
        c.execute('''INSERT INTO kpis (employee_id, month, kpi)
                     VALUES (?, ?, ?)''',
                  (employee_id, get_current_month(), 100))
        
        status_msg = "Xodim qo'shildi"
    
    # Update request status
    c.execute("UPDATE registration_requests SET status = 'accepted' WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()
    
    # Notify user
    try:
        await bot.send_message(
            request['telegram_id'],
            f"🎉 **Tabriklaymiz!**\n\n"
            f"✅ Sizning ro'yxatdan o'tish so'rovingiz qabul qilindi!\n\n"
            f"📋 **Sizning ma'lumotlaringiz:**\n"
            f"👤 Ism: {request['name']} {request['surname']}\n"
            f"📱 Telefon: {request['phone']}\n"
            f"💼 Lavozim: {request['position']}\n"
            f"💰 Maosh: {format_number(salary_amount)} so'm\n\n"
            f"🎯 Endi siz o'zingizning maosh, bonus va KPI ma'lumotlaringizni ko'rishingiz mumkin.\n"
            f"Bosh menyuga qaytish uchun /start buyrug'ini bosing."
        )
    except:
        pass
    
    await message.answer(
        f"✅ {status_msg}: {request['name']} {request['surname']}\n"
        f"💰 Maosh: {format_number(salary_amount)} so'm"
    )
    
    await state.clear()
    await message.answer("Bosh menyu:", reply_markup=get_main_menu(message.from_user.id))

@dp.callback_query(lambda c: c.data.startswith("next_reg_"))
async def next_registration(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    current_id = int(callback_query.data.split("_")[2])
    state_data = await state.get_data()
    requests = state_data.get('all_requests', [])
    
    if not requests:
        await callback_query.answer("❌ So'rovlar topilmadi!", show_alert=True)
        return
    
    # Find current index and get next
    current_index = next((i for i, r in enumerate(requests) if r['id'] == current_id), 0)
    next_index = (current_index + 1) % len(requests)
    request = dict(requests[next_index])
    
    text = f"📋 **Ro'yxatdan o'tish so'rovi (#{request['id']}):**\n\n"
    text += f"👤 Ism: {request['name']}\n"
    text += f"👥 Familiya: {request['surname']}\n"
    text += f"📱 Telefon: {request['phone']}\n"
    text += f"💼 Lavozim: {request['position']}\n"
    text += f"💰 Maosh taxmini: {format_number(request['salary_request'])} so'm\n"
    text += f"🆔 Telegram ID: {request['telegram_id']}\n"
    text += f"📅 So'rov sanasi: {request['requested_at'].split()[0] if request['requested_at'] else 'Noma\'lum'}\n\n"
    text += f"📊 Jami {len(requests)} ta yangi so'rov mavjud."
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_{request['id']}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{request['id']}")],
        [InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"next_reg_{request['id']}")],
        [InlineKeyboardButton(text="💵 Maosh belgilash", callback_data=f"setsalary_{request['id']}")],
        get_back_to_admin()[0]
    ]
    
    await state.update_data(current_request_id=request['id'])
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# =============== ADMIN EMPLOYEE MANAGEMENT HANDLERS ===============
@dp.callback_query(lambda c: c.data == "add_employee")
async def add_employee_start(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    await state.set_state(AdminStates.adding_employee)
    await callback_query.message.edit_text(
        "➕ **Yangi xodim qo'shish**\n\n"
        "Xodimning ismini kiriting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
    )

@dp.message(AdminStates.adding_employee)
async def add_employee_name(message: Message, state: FSMContext):
    if len(message.text.strip()) < 2:
        await message.answer("❌ Iltimos, to'g'ri ism kiriting (kamida 2 harf)")
        return
    
    await state.update_data(emp_name=message.text.strip())
    await state.set_state(AdminStates.editing_employee)  # Reuse state for next step
    await message.answer("Familiyani kiriting:")

@dp.callback_query(lambda c: c.data == "edit_employee")
async def edit_employee(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, surname FROM employees ORDER BY name")
    employees = c.fetchall()
    conn.close()
    
    if not employees:
        await callback_query.message.edit_text(
            "📭 **Hozircha xodimlar yo'q.**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
        )
        return
    
    text = "✏️ **Xodimni tahrirlash**\n\n"
    text += "Tahrirlash uchun xodimni tanlang:\n\n"
    
    keyboard = []
    for emp in employees:
        emp_dict = dict(emp)
        keyboard.append([InlineKeyboardButton(
            text=f"{emp_dict['name']} {emp_dict['surname']}", 
            callback_data=f"edit_emp_{emp_dict['id']}"
        )])
    keyboard.append(get_back_to_admin()[0])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data == "delete_employee")
async def delete_employee(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, surname FROM employees ORDER BY name")
    employees = c.fetchall()
    conn.close()
    
    if not employees:
        await callback_query.message.edit_text(
            "📭 **Hozircha xodimlar yo'q.**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
        )
        return
    
    text = "❌ **Xodimni o'chirish**\n\n"
    text += "O'chirish uchun xodimni tanlang:\n\n"
    
    keyboard = []
    for emp in employees:
        emp_dict = dict(emp)
        keyboard.append([InlineKeyboardButton(
            text=f"❌ {emp_dict['name']} {emp_dict['surname']}", 
            callback_data=f"confirm_delete_{emp_dict['id']}"
        )])
    keyboard.append(get_back_to_admin()[0])
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("confirm_delete_"))
async def confirm_delete(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    emp_id = int(callback_query.data.split("_")[2])
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, surname FROM employees WHERE id = ?", (emp_id,))
    employee = c.fetchone()
    
    if not employee:
        await callback_query.answer("❌ Xodim topilmadi!", show_alert=True)
        conn.close()
        return
    
    employee = dict(employee)
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"delete_confirm_{emp_id}")],
        [InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="delete_employee")]
    ]
    
    await callback_query.message.edit_text(
        f"⚠️ **Tasdiqlash**\n\n"
        f"Siz {employee['name']} {employee['surname']}ni o'chirmoqchimisiz?\n"
        f"Bu amalni qaytarib bo'lmaydi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    conn.close()

@dp.callback_query(lambda c: c.data.startswith("delete_confirm_"))
async def delete_confirm(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    emp_id = int(callback_query.data.split("_")[2])
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, surname FROM employees WHERE id = ?", (emp_id,))
    employee = c.fetchone()
    
    if employee:
        employee = dict(employee)
        c.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
        conn.commit()
        await callback_query.answer(f"✅ {employee['name']} {employee['surname']} o'chirildi!", show_alert=True)
    else:
        await callback_query.answer("❌ Xodim topilmadi!", show_alert=True)
    
    conn.close()
    await back_to_admin_menu(callback_query, FSMContext(dp.storage, callback_query.from_user.id, dp.storage))

@dp.callback_query(lambda c: c.data == "manage_employees")
async def manage_employees(callback_query: types.CallbackQuery):
    """View and manage all employees"""
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, surname, position, base_salary, status, created_at FROM employees ORDER BY name")
    employees = c.fetchall()
    conn.close()
    
    if not employees:
        await callback_query.message.edit_text(
            "📭 **Hozircha xodimlar yo'q.**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
        )
        return
    
    text = "👥 **Xodimlar ro'yxati:**\n\n"
    
    keyboard = []
    for emp in employees:
        emp_dict = dict(emp)
        status_emoji = "✅" if emp_dict['status'] == 'active' else "⏳"
        created_date = emp_dict['created_at'].split()[0] if emp_dict['created_at'] else 'Noma\'lum'
        
        emp_info = f"{emp_dict['name']} {emp_dict['surname']}"
        text += f"{status_emoji} {emp_info}\n"
        text += f"   💼 {emp_dict['position']}\n"
        text += f"   💰 {format_number(emp_dict['base_salary'])} so'm\n"
        text += f"   📅 {created_date}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            text=f"{status_emoji} {emp_dict['name']} {emp_dict['surname']}", 
            callback_data=f"emp_detail_{emp_dict['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Refresh", callback_data="manage_employees")])
    keyboard.append(get_back_to_admin()[0])
    
    text += f"📊 Jami: {len(employees)} ta xodim"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("emp_detail_"))
async def employee_detail(callback_query: types.CallbackQuery):
    """View employee details and manage"""
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    emp_id = int(callback_query.data.split("_")[2])
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
    employee = c.fetchone()
    
    if not employee:
        await callback_query.answer("❌ Xodim topilmadi!", show_alert=True)
        conn.close()
        return
    
    emp_dict = dict(employee)
    
    # Get this month's statistics
    month = get_current_month()
    c.execute("SELECT SUM(amount) as total FROM bonuses WHERE employee_id = ? AND strftime('%Y-%m', date) = ?",
              (emp_id, month))
    bonus_result = c.fetchone()
    total_bonus = bonus_result['total'] or 0
    
    c.execute("SELECT SUM(amount) as total FROM penalties WHERE employee_id = ? AND strftime('%Y-%m', date) = ?",
              (emp_id, month))
    penalty_result = c.fetchone()
    total_penalty = penalty_result['total'] or 0
    
    c.execute("SELECT kpi FROM kpis WHERE employee_id = ? AND month = ?", (emp_id, month))
    kpi_result = c.fetchone()
    kpi = kpi_result['kpi'] if kpi_result else 100
    
    conn.close()
    
    text = f"👤 **Xodim tafsilotlari:**\n\n"
    text += f"👤 Ism: {emp_dict['name']} {emp_dict['surname']}\n"
    text += f"💼 Lavozim: {emp_dict.get('position', 'Noma\'lum')}\n"
    text += f"📱 Telefon: {emp_dict.get('phone', 'Noma\'lum')}\n"
    text += f"💰 Asosiy maosh: {format_number(emp_dict['base_salary'])} so'm\n"
    text += f"📊 Rol: {emp_dict['role']}\n"
    text += f"🔖 Holat: {'✅ Faol' if emp_dict['status'] == 'active' else '⏳ Kutilmoqda'}\n"
    text += f"📅 Ro'yxatdan o'tgan: {emp_dict.get('created_at', 'Noma\'lum').split()[0]}\n\n"
    
    text += f"**{month} oyining statistikasi:**\n"
    text += f"🎁 Bonuslar: {format_number(total_bonus)} so'm\n"
    text += f"⚠️ Jarimalar: {format_number(total_penalty)} so'm\n"
    text += f"📈 KPI: {kpi}%\n"
    
    keyboard = [
        [InlineKeyboardButton(text="✏️ Maosh o'zgartirish", callback_data=f"change_salary_{emp_id}")],
        [InlineKeyboardButton(text="🔖 Holat o'zgartirish", callback_data=f"change_status_{emp_id}")],
        [InlineKeyboardButton(text="❌ O'chirish", callback_data=f"confirm_delete_{emp_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="manage_employees")]
    ]
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("change_status_"))
async def change_status(callback_query: types.CallbackQuery):
    """Change employee status"""
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    emp_id = int(callback_query.data.split("_")[2])
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, surname, status FROM employees WHERE id = ?", (emp_id,))
    employee = c.fetchone()
    conn.close()
    
    if not employee:
        await callback_query.answer("❌ Xodim topilmadi!", show_alert=True)
        return
    
    emp_dict = dict(employee)
    new_status = 'pending' if emp_dict['status'] == 'active' else 'active'
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE employees SET status = ? WHERE id = ?", (new_status, emp_id))
    conn.commit()
    conn.close()
    
    status_text = '✅ Faol' if new_status == 'active' else '⏳ Kutilmoqda'
    await callback_query.answer(f"✅ {emp_dict['name']} {emp_dict['surname']}ning holati {status_text}ga o'zgartirildi!", show_alert=True)
    
    # Refresh employee details
    await employee_detail(callback_query)

@dp.callback_query(lambda c: c.data.startswith("change_salary_"))
async def change_salary(callback_query: types.CallbackQuery, state: FSMContext):
    """Change employee salary"""
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    emp_id = int(callback_query.data.split("_")[2])
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name, surname, base_salary FROM employees WHERE id = ?", (emp_id,))
    employee = c.fetchone()
    conn.close()
    
    if not employee:
        await callback_query.answer("❌ Xodim topilmadi!", show_alert=True)
        return
    
    emp_dict = dict(employee)
    await state.update_data(emp_id=emp_id, emp_name=emp_dict['name'], emp_surname=emp_dict['surname'])
    await state.set_state(AdminStates.editing_employee)
    
    await callback_query.message.edit_text(
        f"💰 **Maosh o'zgartirish**\n\n"
        f"👤 {emp_dict['name']} {emp_dict['surname']}\n"
        f"Joriy maosh: {format_number(emp_dict['base_salary'])} so'm\n\n"
        f"Yangi maosh kiriting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
    )

@dp.message(AdminStates.editing_employee)
async def process_salary_change(message: Message, state: FSMContext):
    """Process salary change"""
    salary_text = message.text.strip()
    if not salary_text:
        await message.answer("❌ Iltimos, maosh kiriting")
        return
    
    salary_amount = parse_salary(salary_text)
    
    if salary_amount <= 0:
        await message.answer("❌ Maosh noto'g'ri kiritildi. Iltimos, raqam kiriting")
        return
    
    state_data = await state.get_data()
    emp_id = state_data.get('emp_id')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE employees SET base_salary = ? WHERE id = ?", (salary_amount, emp_id))
    conn.commit()
    conn.close()
    
    await message.answer(
        f"✅ Maosh yangilandi: {format_number(salary_amount)} so'm"
    )
    
    await state.clear()
    await message.answer("Bosh menyu:", reply_markup=get_main_menu(message.from_user.id))

@dp.callback_query(lambda c: c.data == "add_bonus")
async def add_bonus_start(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, surname FROM employees ORDER BY name")
    employees = c.fetchall()
    conn.close()
    
    if not employees:
        await callback_query.message.edit_text(
            "📭 **Hozircha xodimlar yo'q.**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
        )
        return
    
    keyboard = []
    for emp in employees:
        emp_dict = dict(emp)
        keyboard.append([InlineKeyboardButton(
            text=f"🎁 {emp_dict['name']} {emp_dict['surname']}", 
            callback_data=f"bon_{emp_dict['id']}"
        )])
    keyboard.append(get_back_to_admin()[0])
    
    await callback_query.message.edit_text(
        "💰 **Bonus berish**\n\n"
        "Bonus berish uchun xodimni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("bon_"))
async def bonus_amount(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    emp_id = int(callback_query.data.split("_")[1])
    await state.set_state(AdminStates.adding_bonus)
    await state.update_data(bonus_emp_id=emp_id)
    
    await callback_query.message.edit_text(
        "Bonus miqdorini kiriting (sonlari):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
    )

@dp.message(AdminStates.adding_bonus)
async def bonus_reason(message: Message, state: FSMContext):
    amount = parse_salary(message.text.strip())
    
    if amount <= 0:
        await message.answer("❌ Noto'g'ri miqdor! Iltimos, raqam kiriting")
        return
    
    await state.update_data(bonus_amount=amount)
    await message.answer("Bonus sababini kiriting:")

@dp.callback_query(lambda c: c.data == "add_penalty")
async def add_penalty_start(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, surname FROM employees ORDER BY name")
    employees = c.fetchall()
    conn.close()
    
    if not employees:
        await callback_query.message.edit_text(
            "📭 **Hozircha xodimlar yo'q.**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
        )
        return
    
    keyboard = []
    for emp in employees:
        emp_dict = dict(emp)
        keyboard.append([InlineKeyboardButton(
            text=f"⚠️ {emp_dict['name']} {emp_dict['surname']}", 
            callback_data=f"pen_{emp_dict['id']}"
        )])
    keyboard.append(get_back_to_admin()[0])
    
    await callback_query.message.edit_text(
        "⚠️ **Jarima berish**\n\n"
        "Jarima berish uchun xodimni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("pen_"))
async def penalty_amount(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    emp_id = int(callback_query.data.split("_")[1])
    await state.set_state(AdminStates.adding_penalty)
    await state.update_data(penalty_emp_id=emp_id)
    
    await callback_query.message.edit_text(
        "Jarima miqdorini kiriting (sonlari):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
    )

@dp.message(AdminStates.adding_penalty)
async def penalty_reason(message: Message, state: FSMContext):
    amount = parse_salary(message.text.strip())
    
    if amount <= 0:
        await message.answer("❌ Noto'g'ri miqdor! Iltimos, raqam kiriting")
        return
    
    await state.update_data(penalty_amount=amount)
    await message.answer("Jarima sababini kiriting:")

@dp.callback_query(lambda c: c.data == "add_kpi")
async def add_kpi_start(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, surname FROM employees ORDER BY name")
    employees = c.fetchall()
    conn.close()
    
    if not employees:
        await callback_query.message.edit_text(
            "📭 **Hozircha xodimlar yo'q.**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
        )
        return
    
    keyboard = []
    for emp in employees:
        emp_dict = dict(emp)
        keyboard.append([InlineKeyboardButton(
            text=f"📈 {emp_dict['name']} {emp_dict['surname']}", 
            callback_data=f"kpi_{emp_dict['id']}"
        )])
    keyboard.append(get_back_to_admin()[0])
    
    await callback_query.message.edit_text(
        "📈 **KPI qo'shish**\n\n"
        "KPI kiritish uchun xodimni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("kpi_"))
async def kpi_value(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    emp_id = int(callback_query.data.split("_")[1])
    await state.set_state(AdminStates.adding_kpi)
    await state.update_data(kpi_emp_id=emp_id)
    
    await callback_query.message.edit_text(
        "KPI qiymatini kiriting (% - misol: 100, 110, 95):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
    )

@dp.message(AdminStates.adding_kpi)
async def kpi_save(message: Message, state: FSMContext):
    try:
        kpi_value = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Iltimos, raqam kiriting (100, 110, 95 kabi)")
        return
    
    if kpi_value < 0 or kpi_value > 200:
        await message.answer("❌ KPI 0 dan 200 gacha bo'lishi kerak")
        return
    
    state_data = await state.get_data()
    emp_id = state_data.get('kpi_emp_id')
    month = get_current_month()
    
    conn = get_db()
    c = conn.cursor()
    
    # Check if KPI exists for this month
    c.execute("SELECT id FROM kpis WHERE employee_id = ? AND month = ?", (emp_id, month))
    existing = c.fetchone()
    
    if existing:
        c.execute("UPDATE kpis SET kpi = ? WHERE employee_id = ? AND month = ?", 
                 (kpi_value, emp_id, month))
    else:
        c.execute("INSERT INTO kpis (employee_id, month, kpi) VALUES (?, ?, ?)", 
                 (emp_id, month, kpi_value))
    
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ KPI {kpi_value}% saqlandi!")
    await message.answer("Bosh menyu:", reply_markup=get_main_menu(message.from_user.id))

@dp.callback_query(lambda c: c.data == "stats")
async def show_stats(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    conn = get_db()
    c = conn.cursor()
    
    # Get total employees
    c.execute("SELECT COUNT(*) as count FROM employees")
    total_employees = c.fetchone()['count']
    
    # Get total salaries
    c.execute("SELECT SUM(base_salary) as total FROM employees")
    total_salary = c.fetchone()['total'] or 0
    
    # Get pending registrations
    c.execute("SELECT COUNT(*) as count FROM registration_requests WHERE status = 'pending'")
    pending_regs = c.fetchone()['count']
    
    conn.close()
    
    text = f"📊 **Statistika:**\n\n"
    text += f"👥 Jami xodimlar: {total_employees}\n"
    text += f"💰 Jami maosh: {format_number(total_salary)} so'm\n"
    text += f"📋 Kutilayotgan so'rovlar: {pending_regs}\n"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
    )

@dp.callback_query(lambda c: c.data == "calculate")
async def calculate_salaries(callback_query: types.CallbackQuery):
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
        return
    
    month = get_current_month()
    
    conn = get_db()
    c = conn.cursor()
    
    # Get all employees
    c.execute("SELECT id, base_salary FROM employees")
    employees = c.fetchall()
    
    calculated = 0
    for emp in employees:
        emp_dict = dict(emp)
        emp_id = emp_dict['id']
        base_salary = emp_dict['base_salary']
        
        # Get bonuses, penalties, KPI
        total_bonus = get_total_bonus(emp_id, month)
        total_penalty = get_total_penalty(emp_id, month)
        
        c.execute("SELECT kpi FROM kpis WHERE employee_id = ? AND month = ?", (emp_id, month))
        kpi_row = c.fetchone()
        kpi = kpi_row['kpi'] if kpi_row else 100
        
        kpi_bonus = base_salary * (kpi - 100) / 100 if kpi > 100 else 0
        total = base_salary + total_bonus + kpi_bonus - total_penalty
        
        # Check if salary record exists
        c.execute("SELECT id FROM salaries WHERE employee_id = ? AND month = ?", (emp_id, month))
        exists = c.fetchone()
        
        if exists:
            c.execute('''UPDATE salaries 
                         SET base_salary = ?, bonus = ?, penalty = ?, kpi = ?, kpi_bonus = ?, total = ?
                         WHERE employee_id = ? AND month = ?''',
                     (base_salary, total_bonus, total_penalty, kpi, kpi_bonus, total, emp_id, month))
        else:
            c.execute('''INSERT INTO salaries 
                         (employee_id, month, base_salary, bonus, penalty, kpi, kpi_bonus, total)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (emp_id, month, base_salary, total_bonus, total_penalty, kpi, kpi_bonus, total))
        
        calculated += 1
    
    conn.commit()
    conn.close()
    
    await callback_query.answer(f"✅ {calculated} ta xodimning maoshi hisoblandi!", show_alert=True)
    await callback_query.message.edit_text(
        "👨‍💼 **Admin paneliga xush kelibsiz!**\n"
        "Quyidagi menyudan kerakli amalni tanlang:",
        reply_markup=get_main_menu(callback_query.from_user.id)
    )

@dp.callback_query(lambda c: c.data == "help")
async def show_help(callback_query: types.CallbackQuery):
    text = f"ℹ️ **Yordam**\n\n"
    text += f"Bu bot orqali siz:\n"
    text += f"• 💰 Mening maoshimi ko'rish\n"
    text += f"• 📈 Mening KPI'imni ko'rish\n"
    text += f"• 🎁 Bonuslarimni ko'rish\n"
    text += f"• ⚠️ Jarimalarimni ko'rish\n"
    text += f"• 📊 Hisobotlarni ko'rish\n\n"
    text += f"Admin uchun:\n"
    text += f"• ➕ Xodim qo'shish\n"
    text += f"• ✏️ Xodimni tahrirlash\n"
    text += f"• ❌ Xodimni o'chirish\n"
    text += f"• 💰 Bonus berish\n"
    text += f"• ⚠️ Jarima berish\n"
    text += f"• 📈 KPI qo'shish\n"
    text += f"• 📊 Statistikani ko'rish\n"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.callback_query(lambda c: c.data == "report")
async def show_report(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    employee = get_employee_by_telegram_id(telegram_id)
    
    if not employee:
        await callback_query.answer("❌ Siz xodim emassiz!", show_alert=True)
        return
    
    month = get_current_month()
    
    text = f"📊 **Hisobot - {month}**\n\n"
    text += f"👤 Xodim: {employee['name']} {employee['surname']}\n"
    text += f"💼 Lavozim: {employee.get('position', 'Noma\'lum')}\n"
    text += f"🏢 Asosiy maosh: {format_number(employee['base_salary'])} so'm\n\n"
    
    text += f"📈 **Oylik statistika:**\n"
    
    # Get bonuses
    total_bonus = get_total_bonus(employee['id'], month)
    text += f"🎁 Bonuslar: {format_number(total_bonus)} so'm\n"
    
    # Get penalties
    total_penalty = get_total_penalty(employee['id'], month)
    text += f"⚠️ Jarimalar: {format_number(total_penalty)} so'm\n"
    
    # Get KPI
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT kpi FROM kpis WHERE employee_id = ? AND month = ?", 
             (employee['id'], month))
    kpi_row = c.fetchone()
    conn.close()
    
    kpi = kpi_row['kpi'] if kpi_row else 100
    text += f"📊 KPI: {kpi}%\n"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.callback_query(lambda c: c.data == "kpi")
async def show_kpi(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    employee = get_employee_by_telegram_id(telegram_id)
    
    if not employee:
        await callback_query.answer("❌ Siz xodim emassiz!", show_alert=True)
        return
    
    month = get_current_month()
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT kpi, details FROM kpis WHERE employee_id = ? AND month = ?", 
             (employee['id'], month))
    kpi_row = c.fetchone()
    conn.close()
    
    if not kpi_row:
        text = f"📈 **Mening KPI'im:**\n\n"
        text += f"Hozircha {month} uchun KPI kiritilmagan.\n"
        text += f"Default KPI: 100%"
    else:
        kpi_row = dict(kpi_row)
        text = f"📈 **Mening KPI'im:**\n\n"
        text += f"📅 Oy: {month}\n"
        text += f"📊 KPI: {kpi_row['kpi']}%\n"
        if kpi_row['details']:
            text += f"📝 Izoh: {kpi_row['details']}"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.callback_query(lambda c: c.data == "bonus")
async def show_bonus(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    employee = get_employee_by_telegram_id(telegram_id)
    
    if not employee:
        await callback_query.answer("❌ Siz xodim emassiz!", show_alert=True)
        return
    
    month = get_current_month()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT amount, reason, date FROM bonuses 
                 WHERE employee_id = ? AND strftime('%Y-%m', date) = ?
                 ORDER BY date DESC''',
             (employee['id'], month))
    bonuses = c.fetchall()
    conn.close()
    
    total_bonus = get_total_bonus(employee['id'], month)
    
    text = f"🎁 **Bonuslarim - {month}:**\n\n"
    text += f"Jami bonus: {format_number(total_bonus)} so'm\n\n"
    
    if bonuses:
        text += "**Bonuslar ro'yxati:**\n"
        for bonus in bonuses:
            bonus_dict = dict(bonus)
            text += f"\n• {bonus_dict['reason']}: {format_number(bonus_dict['amount'])} so'm\n"
    else:
        text += "Hozircha bonus yo'q"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.callback_query(lambda c: c.data == "penalty")
async def show_penalty(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    employee = get_employee_by_telegram_id(telegram_id)
    
    if not employee:
        await callback_query.answer("❌ Siz xodim emassiz!", show_alert=True)
        return
    
    month = get_current_month()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT amount, reason, date FROM penalties 
                 WHERE employee_id = ? AND strftime('%Y-%m', date) = ?
                 ORDER BY date DESC''',
             (employee['id'], month))
    penalties = c.fetchall()
    conn.close()
    
    total_penalty = get_total_penalty(employee['id'], month)
    
    text = f"⚠️ **Jarimalarim - {month}:**\n\n"
    text += f"Jami jarima: {format_number(total_penalty)} so'm\n\n"
    
    if penalties:
        text += "**Jarimalar ro'yxati:**\n"
        for penalty in penalties:
            penalty_dict = dict(penalty)
            text += f"\n• {penalty_dict['reason']}: {format_number(penalty_dict['amount'])} so'm\n"
    else:
        text += "Hozircha jarima yo'q"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

@dp.callback_query(lambda c: c.data == "profile")
async def show_profile(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    employee = get_employee_by_telegram_id(telegram_id)
    
    if not employee:
        await callback_query.answer("❌ Siz xodim emassiz!", show_alert=True)
        return
    
    text = f"👤 **Mening profilim:**\n\n"
    text += f"👤 Ism: {employee['name']}\n"
    text += f"👥 Familiya: {employee['surname']}\n"
    text += f"📱 Telefon: {employee.get('phone', 'Kiritilmagan')}\n"
    text += f"💼 Lavozim: {employee.get('position', 'Kiritilmagan')}\n"
    text += f"💰 Asosiy maosh: {format_number(employee['base_salary'])} so'm\n"
    text += f"📅 Ro'yxatdan o'tgan sana: {employee.get('created_at', 'Noma\'lum').split()[0] if employee.get('created_at') else 'Noma\'lum'}\n"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_button())
    )

# =============== BACK BUTTON HANDLERS ===============
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    telegram_id = callback_query.from_user.id
    await state.clear()
    await cmd_start(callback_query.message)

@dp.callback_query(lambda c: c.data == "back_to_admin_menu")
async def back_to_admin_menu(callback_query: types.CallbackQuery, state: FSMContext):
    telegram_id = callback_query.from_user.id
    if telegram_id in ADMIN_IDS:
        await state.clear()
        await callback_query.message.edit_text(
            "👨‍💼 **Admin paneliga xush kelibsiz!**\n"
            "Quyidagi menyudan kerakli amalni tanlang:",
            reply_markup=get_main_menu(telegram_id)
        )
    else:
        await callback_query.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)

@dp.callback_query(lambda c: c.data == "salary")
async def show_salary(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    
    employee = get_employee_by_telegram_id(telegram_id)
    if not employee:
        await callback_query.answer("❌ Siz xodim emassiz!", show_alert=True)
        return
    
    employee_id = employee['id']
    month = get_current_month()
    
    base_salary = employee['base_salary']
    total_bonus = get_total_bonus(employee_id, month)
    total_penalty = get_total_penalty(employee_id, month)
    
    # Get KPI
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT kpi FROM kpis 
                 WHERE employee_id = ? AND month = ?''',
              (employee_id, month))
    kpi_row = c.fetchone()
    kpi = kpi_row['kpi'] if kpi_row else 100
    
    kpi_bonus = base_salary * (kpi - 100) / 100 if kpi > 100 else 0
    total = base_salary + total_bonus + kpi_bonus - total_penalty
    
    conn.close()
    
    text = f"💰 **Mening maoshim:**\n\n"
    text += f"📅 Oy: {month}\n"
    text += f"🏢 Asosiy maosh: {format_number(base_salary)} so'm\n"
    text += f"📈 Bonus: +{format_number(total_bonus)} so'm\n"
    text += f"📉 Jarima: -{format_number(total_penalty)} so'm\n"
    text += f"🔢 KPI: {kpi}%\n"
    text += f"💵 KPI bonus: {format_number(kpi_bonus)} so'm\n"
    text += f"📊 Jami: **{format_number(total)} so'm**"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=get_back_button())
    await callback_query.message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "start_employee")
async def start_employee(callback_query: types.CallbackQuery):
    telegram_id = callback_query.from_user.id
    
    employee = get_employee_by_telegram_id(telegram_id)
    if not employee:
        await callback_query.answer("❌ Siz xodim emassiz!", show_alert=True)
        return
    
    await callback_query.message.edit_text(
        f"👤 **Xush kelibsiz, {employee.get('name', 'Xodim')}!**\n"
        "Quyidagi menyudan kerakli ma'lumotni tanlang:",
        reply_markup=get_main_menu(telegram_id)
    )

# =============== COMMANDS FOR ADMINS ===============
@dp.message(Command("registrations"))
async def cmd_registrations(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizda admin huquqlari yo'q!")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM registration_requests WHERE status = 'pending' ORDER BY requested_at DESC")
    requests = c.fetchall()
    conn.close()
    
    if not requests:
        await message.answer(
            "📭 **Hozircha yangi so'rovlar yo'q.**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=get_back_to_admin())
        )
        return
    
    # Birinchi so'rovni ko'rsatish
    request = dict(requests[0])
    
    text = f"📋 **Ro'yxatdan o'tish so'rovi (#{request['id']}):**\n\n"
    text += f"👤 Ism: {request['name']}\n"
    text += f"👥 Familiya: {request['surname']}\n"
    text += f"📱 Telefon: {request['phone']}\n"
    text += f"💼 Lavozim: {request['position']}\n"
    text += f"💰 Maosh taxmini: {format_number(request['salary_request'])} so'm\n"
    text += f"🆔 Telegram ID: {request['telegram_id']}\n"
    text += f"📅 So'rov sanasi: {request['requested_at'].split()[0] if request['requested_at'] else 'Noma\'lum'}\n\n"
    text += f"📊 Jami {len(requests)} ta yangi so'rov mavjud."
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_{request['id']}")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{request['id']}")],
        [InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"next_reg_{request['id']}")],
        [InlineKeyboardButton(text="💵 Maosh belgilash", callback_data=f"setsalary_{request['id']}")],
        get_back_to_admin()[0]
    ]
    
    await state.update_data(current_request_id=request['id'], all_requests=requests)
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# =============== DEFAULT HANDLER ===============
@dp.message()
async def handle_other_messages(message: Message):
    if message.text.startswith('/'):
        await message.answer("Iltimos, menyudan kerakli amalni tanlang yoki /start buyrug'ini bosing.")
    else:
        # Check if user is in registration process
        telegram_id = message.from_user.id
        employee = get_employee_by_telegram_id(telegram_id)
        if not employee and telegram_id not in ADMIN_IDS:
            await message.answer(
                "🤝 **Xush kelibsiz!**\n\n"
                "Ma'lumotlaringizni ko'rish uchun avval ro'yxatdan o'ting.\n"
                "Ro'yxatdan o'tish uchun quyidagi tugmani bosing:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", callback_data="register")]
                ])
            )
        else:
            await message.answer(
                "Iltimos, menyudan kerakli amalni tanlang yoki /start buyrug'ini bosing."
            )

# =============== MAIN FUNCTION ===============
async def main():
    print("🤖 Bot ishga tushmoqda...")
    init_database()  # Initialize database on startup
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())