from flask import Flask, render_template, request, redirect, url_for, session
import os
import datetime

app = Flask(__name__)
app.secret_key = 'amit'

# Files
USERS_FILE = 'users.txt'
TRANSACTIONS_DIR = 'transactions'

if not os.path.exists(TRANSACTIONS_DIR):
    os.mkdir(TRANSACTIONS_DIR)

# Admin credentials (hardcoded for simplicity)
ADMIN_USERNAME = "060506,dob"
ADMIN_PASSWORD = "060506,dob"

# Helper function to convert timestamp
def convert_timestamp(input_timestamp):
    try:
        parts = input_timestamp.strip().split()
        if len(parts) == 7:  # dd mm yy hh mm ss am/pm
            day, month, year, hour, minute, second, am_pm = parts
            
            if len(year) == 2:
                year = "20" + year  # Example: 25 -> 2025
            elif len(year) == 4:
                year = year  # Keep it as is if 2025 is entered
            else:
                return input_timestamp  # Invalid format
            
            raw_timestamp = f"{day} {month} {year} {hour} {minute} {second} {am_pm.upper()}"
            dt = datetime.datetime.strptime(raw_timestamp, "%d %m %Y %I %M %S %p")
            return dt.strftime("%d-%b-%Y %I:%M:%S %p")
        else:
            return input_timestamp
    except Exception as e:
        print(f"Error converting timestamp: {e}")
        return input_timestamp


# Home page
@app.route('/')
def home():
    return render_template('index.html')

# Create Account
@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        account_number = request.form['account_number']
        pin = request.form['pin']

        # Duplicate check
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users = f.readlines()
                for user in users:
                    existing_acc = user.strip().split(',')[0]
                    if existing_acc == account_number:
                        return "Account number already exists. Please use a different one."

        # Save if not duplicate
        with open(USERS_FILE, 'a') as f:
            f.write(f'{account_number},{pin}\n')

        open(os.path.join(TRANSACTIONS_DIR, f'{account_number}.txt'), 'a').close()
        return redirect(url_for('home'))
    
    return render_template('create_account.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account_number = request.form['account_number']
        pin = request.form['pin']

        # Admin login check
        if account_number == ADMIN_USERNAME and pin == ADMIN_PASSWORD:
            print("Admin login successful.")  # Debugging log
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))  # Should redirect to admin_dashboard

        # User login check
        with open(USERS_FILE, 'r') as f:
            users = f.readlines()
        for user in users:
            acc, user_pin = user.strip().split(',')
            if acc == account_number and user_pin == pin:
                session['account_number'] = account_number
                return redirect(url_for('account_menu'))
        return "Invalid credentials"  # Error message if credentials are invalid
    return render_template('login.html')  # Render login page if GET request

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    # Check if the user is logged in as admin
    if not session.get('is_admin'):
        return redirect(url_for('home'))  # Redirect to home if not admin

    users_data = []
    try:
        with open(USERS_FILE, 'r') as f:
            users = f.readlines()

        for user in users:
            parts = user.strip().split(',')
            if len(parts) >= 2:
                account_number = parts[0]
                password = parts[1]
                users_data.append({
                    'account_number': account_number,
                    'password': password
                })

    except FileNotFoundError:
        print("Required file not found.")
        return redirect(url_for('home'))

    return render_template('admin_dashboard.html', users_data=users_data)
# Account Menu
@app.route('/account_menu')
def account_menu():
    if 'account_number' not in session:
        return redirect(url_for('login'))
    return render_template('account_menu.html')

# Withdraw
@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'account_number' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            amount = int(request.form['amount'])
            reason = request.form['reason']
            date_input = request.form['date']
            account_number = session['account_number']
            trans_file = os.path.join(TRANSACTIONS_DIR, f'{account_number}.txt')

            balance = get_balance(account_number)
            if amount > balance:
                return "Insufficient balance!"

            timestamp = convert_timestamp(date_input) if date_input.strip() else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(trans_file, 'a') as f:
                f.write(f'Withdraw,{amount},{reason},{timestamp}\n')

            return redirect(url_for('account_menu'))
        except ValueError:
            return "Invalid amount!"
    return render_template('withdraw.html')

# Deposit
@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
    if 'account_number' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            amount = int(request.form['amount'])
            reason = request.form['reason']
            date_input = request.form['date']
            account_number = session['account_number']
            trans_file = os.path.join(TRANSACTIONS_DIR, f'{account_number}.txt')

            timestamp = convert_timestamp(date_input) if date_input.strip() else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(trans_file, 'a') as f:
                f.write(f'Deposit,{amount},{reason},{timestamp}\n')

            return redirect(url_for('account_menu'))
        except ValueError:
            return "Invalid amount!"
    return render_template('deposit.html')

# Balance
@app.route('/balance')
def balance():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    account_number = session['account_number']
    transactions_file = os.path.join(TRANSACTIONS_DIR, f'{account_number}.txt')

    balance = get_balance(account_number)

    return render_template('balance.html', balance=balance)

# Helper function to get balance
def get_balance(account_number):
    trans_file = os.path.join(TRANSACTIONS_DIR, f'{account_number}.txt')
    balance = 0
    if os.path.exists(trans_file):
        with open(trans_file, 'r') as f:
            transactions = f.readlines()
        for transaction in transactions:
            parts = transaction.strip().split(',')
            if len(parts) >= 2:
                t_type = parts[0].strip()
                amount = int(parts[1].strip())
                if t_type.lower() == 'deposit':
                    balance += amount
                elif t_type.lower() == 'withdraw':
                    balance -= amount
    return balance


# View history
@app.route('/view_history')
def view_history():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    deposits = []
    withdrawals = []
    given_udari = []
    taken_udari = []
    total_withdrawal = 0
    account_number = session['account_number']
    trans_file = os.path.join(TRANSACTIONS_DIR, f'{account_number}.txt')

    if os.path.exists(trans_file):
        balance = 0  # Initialize balance
        with open(trans_file, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    action = parts[0].strip()
                    amount = float(parts[1].strip())
                    reason = parts[2].strip()
                    timestamp_raw = parts[3].strip()

                    try:
                        dt_obj = datetime.datetime.strptime(timestamp_raw.split('.')[0], "%Y-%m-%d %H:%M:%S")
                        timestamp = dt_obj.strftime("%d-%b-%Y %I:%M:%S %p")
                    except Exception:
                        timestamp = timestamp_raw

                    if action.lower() == 'deposit':
                        balance += amount
                        transaction = {
                            'account': account_number,
                            'amount': amount,
                            'reason': reason,
                            'timestamp': timestamp,
                            'balance': balance
                        }
                        deposits.append(transaction)
                    elif action.lower() == 'withdraw':
                        balance -= amount
                        total_withdrawal += amount
                        transaction = {
                            'account': account_number,
                            'amount': amount,
                            'reason': reason,
                            'timestamp': timestamp,
                            'balance': balance
                        }
                        withdrawals.append(transaction)
                    elif action.lower() == 'given':
                        balance -= amount
                        transaction = {
                            'account': account_number,
                            'amount': amount,
                            'reason': reason,
                            'timestamp': timestamp,
                            'balance': balance
                        }
                        given_udari.append(transaction)
                    elif action.lower() == 'taken':
                        balance += amount
                        transaction = {
                            'account': account_number,
                            'amount': amount,
                            'reason': reason,
                            'timestamp': timestamp,
                            'balance': balance
                        }
                        taken_udari.append(transaction)

    return render_template('view_history.html',
                           deposits=deposits,
                           withdrawals=withdrawals,
                           given_udari=given_udari,
                           taken_udari=taken_udari,
                           total_withdrawal=total_withdrawal)


# Udari (Loan)
@app.route('/udari', methods=['GET', 'POST'])
def udari():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        loan_type = request.form['loan_type']
        amount = int(request.form['amount'])
        reason = request.form['reason']
        date_input = request.form['date']
        account_number = session['account_number']

        if date_input.strip():
            timestamp = convert_timestamp(date_input)
        else:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        account_file = os.path.join(TRANSACTIONS_DIR, f'{account_number}.txt')

        with open(account_file, 'a') as f:
            f.write(f'{loan_type.capitalize()},{amount},{reason},{timestamp}\n')

        return redirect(url_for('account_menu'))

    return render_template('udari.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)