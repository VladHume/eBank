import pdfkit
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
import random

app = Flask(__name__)

app.config['SECRET_KEY'] = '1234'
# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'banksystem'

mysql = MySQL(app)

config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

@app.route('/')
def index():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login')
def login():
    session.clear()
    return render_template('index.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        surname = request.form['surname']
        name = request.form['name']
        patronymic = request.form['patronymic']
        phone_number = request.form['phone number'].lstrip('+38')
        password = request.form['password']
        passport_id = request.form['passport id']
        address = request.form['address']
        email = request.form['email']
        taxpayer_card_id = request.form['taxpayer card id']

        cursor = mysql.connection.cursor()
        cursor.execute("""
                    SELECT COUNT(*) FROM client
                    WHERE phone_number = %s OR passport_id = %s OR email = %s OR taxpayer_card_id = %s
                """, (phone_number, passport_id, email, taxpayer_card_id))

        result = cursor.fetchone()

        if result[0] > 0:
            flash('Помилка: Номер телефону, паспорт, email або ідентифікаційний код вже існують у системі', 'error')
            return redirect(url_for('add_client'))

        try:
            login = phone_number
            sql_users = """
                    INSERT INTO users 
                    (password, login) 
                    VALUES (%s, %s)
                    """
            values_users = (password, login)
            cursor.execute(sql_users, values_users)

            user_id = cursor.lastrowid

            sql_client = """
                    INSERT INTO client 
                    (surname, name, patronymic, phone_number, passport_id, address, email, taxpayer_card_id, user_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
            values_client = (surname, name, patronymic, phone_number, passport_id, address, email, taxpayer_card_id, user_id)
            cursor.execute(sql_client, values_client)

            mysql.connection.commit()
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Упс, сталася помилка', 'error')
            return redirect(url_for('add_client'))
        finally:
            cursor.close()

    return render_template('register.html')

@app.route('/creating_account_screen')
def creating_account_screen():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT account_type_id, type FROM account_types")
    account_types = cursor.fetchall()
    cursor.close()
    return render_template('creating_account_screen.html', account_types=account_types)

@app.route('/login_user', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')

        if password:
            password = password.lstrip('+38')

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE login = %s", (login,))
        user = cursor.fetchone()
        session.clear()
        if user and user[1] == password:
            session['user_id'] = user[0]

            cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user[0],))
            client = cursor.fetchone()

            if client:
                client_id = client[0]
                cursor.execute("SELECT * FROM account WHERE client_id = %s", (client_id,))
                account = cursor.fetchone()

                if account:
                    return redirect(url_for('home_screen'))
                else:
                    flash('Акаунт не знайдено, перейдіть до створення.', 'warning')
                    return redirect(url_for('creating_account_screen'))
            else:
                flash('Клієнт не знайдений.', 'error')
                return redirect(url_for('add_client'))
        else:
            flash('Невірний логін або пароль', 'error')
            return redirect(url_for('index'))

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        account_type = request.form.get('account_type')
        account_limit = request.form.get('account_limit')

        if account_type and account_limit:
            user_id = session['user_id']

            cursor = mysql.connection.cursor()
            cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
            client_id = cursor.fetchone()

            if client_id:
                client_id = client_id[0]

                opening_date = datetime.now()

                status = 'active'

                cursor.execute("""
                    INSERT INTO account (client_id, account_type, opening_date, account_limit, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (client_id, account_type, opening_date, account_limit, status))

                mysql.connection.commit()
                cursor.close()

                return redirect(url_for('home_screen'))
            else:
                flash('Client not found for the given user ID.', 'error')
                return redirect(url_for('create_account'))
        else:
            flash('Будь ласка, заповніть всі поля', 'error')
            return redirect(url_for('create_account'))

    return render_template('creating_account_screen.html')

@app.route('/home_screen')
def home_screen():
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401

    try:
        cursor = mysql.connection.cursor()

        # Get client_id from client table
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            return "Клієнт не знайдений", 404

        client_id = client[0]

        # Get accounts of type 1 from the account table
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            return "Акаунти не знайдені", 404

        account_ids = [account[0] for account in accounts]

        # Ensure account_ids is a tuple, even if it has only one account_id
        if len(account_ids) == 1:
            account_ids = (account_ids[0],)  # make it a tuple

        # Get card account information from the card_account table
        cursor.execute("""
                SELECT card_account_id, credit_number, my_money, sum, credit_limit, exporation_date, cvv_code, card_type, curr_id, payment_system_id
                FROM card_account WHERE account_id IN %s
            """, (account_ids,))
        cards = cursor.fetchall()

        if not cards:
            return redirect(url_for('creating_card'))

        card_list = []

        for card in cards:
            cursor.execute("SELECT name FROM currency_conversion WHERE currency_id = %s", (card[8],))
            currency = cursor.fetchone()[0]

            cursor.execute("SELECT name FROM payment_systems WHERE payment_system_id = %s", (card[9],))
            payment_system = cursor.fetchone()[0]
            card_info = {
                "card_account_id": card[0],
                "credit_number": card[1],
                "my_money": card[2],
                "sum": card[3],
                "credit_limit": card[4],
                "exporation_date": card[5],
                "cvv_code": card[6],
                "currency": currency,
                "payment_system": payment_system
            }

            # Get card type information
            cursor.execute("SELECT type FROM card_types WHERE card_type_id = %s", (card[7],))
            card_type = cursor.fetchone()
            if card_type:
                card_info["card_type"] = card_type[0]
            else:
                card_info["card_type"] = "Невідомий тип"

            # Get the last 3 transactions related to the card_account_id and identify transaction type
            cursor.execute("""
                SELECT t.sum, t.date, t.status, t.payer_id, t.receiver_id, t.currency
                FROM transaction t
                WHERE t.receiver_id = %s OR t.payer_id = %s
                ORDER BY t.transaction_id DESC LIMIT 3
            """, (card[0], card[0]))

            transactions = cursor.fetchall()

            transaction_list = []

            for t in transactions:
                if len(transaction_list) >= 6:
                    break
                transaction_type = '+' if t[4] == card[0] else '-'
                cursor.execute("""
                                SELECT c.name
                                FROM currency_conversion c
                                WHERE currency_id = %s""", (t[5],))
                currency_name = cursor.fetchone()

                # Check if currency_name exists before accessing it
                currency_name = currency_name[0] if currency_name else "Невідома валюта"

                transaction_info = {
                    "sum": t[0],
                    "date": t[1],
                    "currency": currency_name,
                    "transaction_type": transaction_type
                }
                transaction_list.append(transaction_info)

            card_info["transactions"] = transaction_list
            card_list.append(card_info)

        return render_template('home_screen.html', cards=card_list)
    except Exception as e:
        return f"Помилка: {e}", 500

@app.route('/client_cabinet')
def client_cabinet():
    user_id = session.get('user_id')

    if not user_id:
        flash('Будь ласка, увійдіть до свого акаунту', 'error')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT surname, name, patronymic, phone_number, email, passport_id, address, taxpayer_card_id
        FROM client WHERE user_id = %s
    """, (user_id,))

    client = cursor.fetchone()
    cursor.close()

    if client:
        return render_template('client_cabinet.html', client=client)

    flash('Клієнт не знайдений', 'error')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/update_info', methods=['GET', 'POST'])
def update_info():
    if 'user_id' not in session:
        flash('Будь ласка, увійдіть у систему', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        surname = request.form['surname']
        name = request.form['name']
        patronymic = request.form['patronymic']
        phone_number = request.form['phone number'].lstrip('+38')
        password = request.form['password']
        passport_id = request.form['passport id']
        address = request.form['address']
        email = request.form['email']

        cursor = mysql.connection.cursor()

        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()

        if not client:
            flash('Клієнт не знайдений', 'error')
            return redirect(url_for('update_info'))

        client_id = client[0]

        cursor.execute("""
            SELECT COUNT(*) FROM client
            WHERE (phone_number = %s OR passport_id = %s OR email = %s)
            AND client_id != %s
        """, (phone_number, passport_id, email, client_id))

        result = cursor.fetchone()

        if result[0] > 0:
            flash('Помилка: Номер телефону, паспорт, email або ідентифікаційний код вже існують у системі', 'error')
            return redirect(url_for('update_info'))

        try:
            sql_users = """
                UPDATE users 
                SET password = %s, login = %s
                WHERE user_id = %s
            """
            cursor.execute(sql_users, (password, phone_number, user_id))

            sql_client = """
                UPDATE client 
                SET surname = %s, name = %s, patronymic = %s, phone_number = %s, 
                    passport_id = %s, address = %s, email = %s
                WHERE client_id = %s
            """
            cursor.execute(sql_client, (surname, name, patronymic, phone_number, passport_id, address, email, client_id))

            mysql.connection.commit()
            flash('Дані успішно оновлено', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Упс, сталася помилка', 'error')
            return redirect(url_for('update_info'))
        finally:
            cursor.close()

    return render_template('update_account_info.html')

@app.route('/card_info')
def card_info():
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401

    try:
        cursor = mysql.connection.cursor()

        # Getting client_id from the client table
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            return "Клієнт не знайдений", 404

        client_id = client[0]

        # Getting type 1 accounts from the account table
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            return "Акаунти не знайдені", 404

        account_ids = [account[0] for account in accounts]

        # Getting information about card accounts from the card_account table
        cursor.execute("""
                SELECT card_account_id, credit_number, my_money, sum, credit_limit, exporation_date, cvv_code, card_type, curr_id, payment_system_id
                FROM card_account WHERE account_id IN %s
            """, (tuple(account_ids),))
        cards = cursor.fetchall()

        if not cards:
            return redirect(url_for('creating_card'))

        card_list = []
        for card in cards:
            cursor.execute("SELECT name FROM currency_conversion WHERE currency_id = %s", (card[8],))
            currency = cursor.fetchone()[0]

            cursor.execute("SELECT name FROM payment_systems WHERE payment_system_id = %s", (card[9],))
            payment_system = cursor.fetchone()[0]
            card_info = {
                "card_account_id": card[0],
                "credit_number": card[1],
                "my_money": card[2],
                "sum": card[3],
                "credit_limit": card[4],
                "exporation_date": card[5],
                "cvv_code": card[6],
                "currency": currency,
                "payment_system": payment_system
            }

            # Getting card type by card_type_id
            cursor.execute("SELECT type FROM card_types WHERE card_type_id = %s", (card[7],))
            card_type = cursor.fetchone()
            if card_type:
                card_info["card_type"] = card_type[0]
            else:
                card_info["card_type"] = "Невідомий тип"  # If type not found

            card_list.append(card_info)

        return render_template('card_info.html', cards=card_list)
    except Exception as e:
        return f"Помилка: {e}", 500

def generate_credit_card(payment_system):
    # The first digits are determined by the payment system
    prefix = '4' if payment_system == 1 else '5'
    # Generate a card number (16 digits)
    credit_number = prefix + ''.join(str(random.randint(0, 9)) for _ in range(15))
    # Generate CVV (3 digits)
    cvv = ''.join(str(random.randint(0, 9)) for _ in range(3))
    return credit_number, cvv

def generate_unique_credit_card(cursor, payment_system):
    while True:
        # Card number and CVV generation
        card_number, cvv = generate_credit_card(payment_system)

        # Checking the uniqueness of the card number in the database
        cursor.execute("SELECT COUNT(*) FROM card_account WHERE credit_number = %s", (card_number,))
        if cursor.fetchone()[0] == 0:
            return card_number, cvv

@app.route('/creating_card', methods=['GET', 'POST'])
def creating_card():
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401

    if request.method == 'POST':
        card_type = int(request.form['card_type'])  # Card type: 1 - debit, 2 - credit
        payment_system = int(request.form['payment_system'])  # 1 - VISA, 2 - MasterCard
        currency = int(request.form['currency'])  # Currency (curr_id)
        pin = request.form['PIN']  # PIN

        cursor = mysql.connection.cursor()

        # Generation of a unique card number and CVV
        credit_number, cvv_code = generate_unique_credit_card(cursor, payment_system)

        # Setting a credit limit depending on the type of card
        credit_limit = 0 if card_type == 1 else 20000

        # Getting client_id
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client_id = cursor.fetchone()
        if not client_id:
            return "Клієнт не знайдений", 404

        # Getting account_id
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id[0],))
        account_id = cursor.fetchone()
        if not account_id:
            return "Акаунт не знайдений", 404

        # Adding a record to card_account
        cursor.execute("""
            INSERT INTO card_account (
                account_id, card_type, payment_system_id, sum, my_money, exporation_date, cvv_code, credit_limit, curr_id, pin, credit_number
            )
            VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL 3 YEAR, %s, %s, %s, %s, %s)
        """, (account_id[0], card_type, payment_system, 0, 0, cvv_code, credit_limit, currency, pin, credit_number))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('home_screen'))

    # If it is a GET request, we get data for selecting card types, payment systems and currencies
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM card_types")
    card_types = cursor.fetchall()

    cursor.execute("SELECT * FROM payment_systems")
    payment_systems = cursor.fetchall()

    cursor.execute("SELECT * FROM currency_conversion")
    currencies = cursor.fetchall()

    cursor.close()

    return render_template(
        'creating_card.html',
        card_types=card_types,
        payment_systems=payment_systems,
        currencies=currencies
    )

@app.route('/delete_card/<int:card_id>', methods=['POST'])
def delete_card(card_id):
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401

    try:
        cursor = mysql.connection.cursor()

        # Check if the card belongs to the current user
        cursor.execute("""
            SELECT ca.card_account_id 
            FROM card_account ca 
            JOIN account a ON ca.account_id = a.account_id 
            JOIN client c ON a.client_id = c.client_id 
            WHERE ca.card_account_id = %s AND c.user_id = %s
        """, (card_id, user_id))
        card = cursor.fetchone()

        if not card:
            return "Картку не знайдено або вона не належить користувачеві", 404

        # Removing the card
        cursor.execute("DELETE FROM card_account WHERE card_account_id = %s", (card_id,))
        mysql.connection.commit()

        return "Картку успішно закрито", 200
    except Exception as e:
        return f"Помилка при видаленні картки: {e}", 500
    finally:
        cursor.close()

@app.route('/deposits')
def deposits():
    user_id = session.get('user_id')
    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('home_screen'))

    try:
        cursor = mysql.connection.cursor()

        # Getting client_id from the client table
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            flash("Клієнт не знайдений", 'error')
            return redirect(url_for('home_screen'))

        client_id = client[0]

        # Getting type 1 accounts from the account table
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            flash("Акаунти не знайдені", 'error')
            return redirect(url_for('home_screen'))

        account_ids = [account[0] for account in accounts]

        # Getting information about card accounts from the card_account table
        cursor.execute("""
                    SELECT card_account_id, credit_number, my_money, sum, credit_limit, exporation_date, cvv_code, card_type
                    FROM card_account WHERE account_id IN %s
                """, (tuple(account_ids),))
        cards = cursor.fetchall()

        if not cards:
            return redirect(url_for('creating_card'))

        card_list = []
        for card in cards:
            card_info = {
                "card_account_id": card[0],
                "credit_number": card[1],
                "my_money": card[2],
                "sum": card[3],
                "credit_limit": card[4],
                "exporation_date": card[5],
                "cvv_code": card[6]
            }

            # Getting card type by card_type_id
            cursor.execute("SELECT type FROM card_types WHERE card_type_id = %s", (card[7],))
            card_type = cursor.fetchone()
            if card_type:
                card_info["card_type"] = card_type[0]
            else:
                card_info["card_type"] = "Невідомий тип"

            card_list.append(card_info)

        # Checking the availability of the deposit
        cursor.execute("SELECT * FROM deposits WHERE client_id = %s", (client_id,))
        deposit = cursor.fetchone()

        if deposit:
            # If the deposit exists, we pass its data to the template
            deposit_data = {
                "amount": deposit[4],
                "interest_rate": deposit[5],
                "opening_date": deposit[2],
                "closing_date": deposit[3]
            }
        else:
            deposit_data = None

        return render_template('deposits.html', cards=card_list, deposit_data=deposit_data)

    except Exception as e:
        flash(f"Помилка: {e}", 'error')
        return redirect(url_for('home_screen'))

@app.route('/take_deposit', methods=['GET', 'POST'])
def take_deposit():
    try:
        user_id = session.get('user_id')

        if not user_id:
            flash("Користувач не авторизований", 'error')
            return redirect(url_for('deposits'))

        # Getting deposit data from a form
        credit_number = request.form.get('credit_number')
        opening_date = datetime.today()
        closing_date = request.form.get('closing_date')
        interest_rate = int(request.form.get('interest_rate'))
        deposit_amount = request.form.get('deposit-amount')
        # Getting curr_id for a card
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT curr_id FROM card_account WHERE card_account_id = %s",
            (credit_number,)
        )
        curr_id = cursor.fetchone()
        if not curr_id:
            flash("Щось не так з валютою", 'error')
            return redirect(url_for('deposits'))

        cursor.execute(
            "SELECT payment_system_id FROM card_account WHERE card_account_id = %s",
            (credit_number,)
        )
        payment_system_id = cursor.fetchone()

        if not payment_system_id:
            flash("Щось не так з платіжною системою", 'error')
            return redirect(url_for('deposits'))

        cursor.execute(
            "SELECT sum FROM card_account WHERE card_account_id = %s",
            (credit_number,)
        )

        sum = cursor.fetchone()

        if not sum:
            flash("Щось не так з балансом", 'error')
            return redirect(url_for('deposits'))

        # Getting the rate for conversion into hryvnia
        cursor.execute(
            "SELECT sales_rate FROM currency_conversion WHERE currency_id = %s",
            (curr_id,)
        )
        conversion = cursor.fetchone()

        if not conversion:
            flash("Курс валют не знайдено", 'error')
            return redirect(url_for('deposits'))

        sales_rate = conversion[0]

        deposit_amount_uah = int(deposit_amount) * sales_rate

        if sum[0] < int(deposit_amount):
            flash("На картці недостатньо коштів", 'error')
            return redirect(url_for('deposits'))

        # Card balance update
        cursor.execute(
            "UPDATE card_account SET sum = sum - %s WHERE card_account_id = %s",
            (deposit_amount, credit_number)
        )

        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        # Calling a method to create a transaction
        transaction_data = {
            "sum": deposit_amount,
            "payer_id": credit_number,
            "receiver_id": 0,
            "status": "Completed",
            "payment_system_id": payment_system_id[0],  # Default value
            "currency": curr_id[0],
            "payment_destination": "Поповнення депозиту"
        }
        # Calling the function to create a transaction directly
        create_transaction_response = create_transaction_internal(transaction_data)
        if create_transaction_response.get("error"):
            raise Exception(create_transaction_response["error"])
        # Adding a deposit to the database
        cursor.execute(
            """
            INSERT INTO deposits (client_id, interest_rate, opening_date, closing_date, amount)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (client, interest_rate, opening_date, closing_date, deposit_amount_uah)
        )

        mysql.connection.commit()
        return redirect(url_for('deposits'))

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Помилка : {e}", 'error')
        return redirect(url_for('deposits'))

def create_transaction_internal(data):
    try:
        sum = data['sum']
        payer_id = data['payer_id']
        receiver_id = data['receiver_id']
        status = data.get('status', 'Pending')
        payment_system_id = data['payment_system_id']
        currency = data['currency']
        payment_destination = data['payment_destination']

        # Converting types for correct entry into the database
        sum = int(sum)
        payer_id = int(payer_id)
        receiver_id = int(receiver_id)
        payment_system_id = int(payment_system_id)
        currency = int(currency)

        # Current date
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Adding a transaction to the database
        cursor = mysql.connection.cursor()
        cursor.execute(
            """
            INSERT INTO transaction (sum, date, payer_id, receiver_id, status, payment_system_id, currency, payment_destination)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (sum, date, payer_id, receiver_id, status, payment_system_id, currency, payment_destination)
        )
        mysql.connection.commit()
        return {"message": "Транзакція успішно створена", "transaction_id": cursor.lastrowid}

    except Exception as e:
        mysql.connection.rollback()
        return {"error": str(e)}

@app.route('/transactions')
def transactions():
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401

    try:
        cursor = mysql.connection.cursor()

        # Get client_id from the client table
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            return "Клієнт не знайдений", 404

        client_id = client[0]

        # We get type 1 accounts from the account table
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            return "Акаунти не знайдені", 404

        account_ids = [account[0] for account in accounts]

        # If account_ids contains only one value, provide it as a tuple
        if len(account_ids) == 1:
            account_ids = (account_ids[0],)  # we make a tuple

        # We get information about cards from the card_account table
        cursor.execute("""
                    SELECT card_account_id, credit_number, my_money, sum, credit_limit, exporation_date, cvv_code, card_type
                    FROM card_account WHERE account_id IN %s
                """, (account_ids,))
        cards = cursor.fetchall()

        if not cards:
            return redirect(url_for('creating_card'))

        card_list = []

        for card in cards:
            card_info = {
                "card_account_id": card[0],
                "credit_number": card[1],
                "my_money": card[2],
                "sum": card[3],
                "credit_limit": card[4],
                "exporation_date": card[5],
                "cvv_code": card[6]
            }

            # We get the card type
            cursor.execute("SELECT type FROM card_types WHERE card_type_id = %s", (card[7],))
            card_type = cursor.fetchone()
            if card_type:
                card_info["card_type"] = card_type[0]
            else:
                card_info["card_type"] = "Невідомий тип"

            cursor.execute("""
                    SELECT t.sum, t.date, t.status, t.payer_id, t.receiver_id, t.currency, t.payment_destination, t.transaction_id
                    FROM transaction t
                    WHERE t.receiver_id = %s OR t.payer_id = %s
                    ORDER BY t.transaction_id DESC
                """, (card[0], card[0]))

            transactions = cursor.fetchall()

            transaction_list = []

            for t in transactions:
                # If we send money to ourselves (payer_id = receiver_id), we add two transactions
                if t[3] == t[4]:
                    # First transaction - receipt
                    cursor.execute("""
                        SELECT c.name
                        FROM currency_conversion c
                        WHERE currency_id = %s""", (t[5],))
                    currency_name = cursor.fetchone()
                    currency_name = currency_name[0] if currency_name else "Невідома валюта"

                    transaction_info = {
                        "sum": t[0],
                        "date": t[1],
                        "currency": currency_name,
                        "transaction_type": '+',
                        "status": t[2],
                        "payer_id": t[3],
                        "receiver_id": t[4],
                        "payment_destination": t[6],
                        "transaction_id": t[7]
                    }
                    transaction_list.append(transaction_info)

                    transaction_info = {
                        "sum": t[0],
                        "date": t[1],
                        "currency": currency_name,
                        "transaction_type": '-',
                        "status": t[2],
                        "payer_id": t[3],
                        "receiver_id": t[4],
                        "payment_destination": t[6],
                        "transaction_id": t[7]
                    }
                    transaction_list.append(transaction_info)
                else:
                    # If payer_id and receiver_id are different, add a regular transaction
                    transaction_type = '+' if t[4] == card[0] else '-'

                    cursor.execute("""
                        SELECT c.name
                        FROM currency_conversion c
                        WHERE currency_id = %s""", (t[5],))
                    currency_name = cursor.fetchone()
                    currency_name = currency_name[0] if currency_name else "Невідома валюта"

                    transaction_info = {
                        "sum": t[0],
                        "date": t[1],
                        "currency": currency_name,
                        "transaction_type": transaction_type,
                        "status": t[2],
                        "payer_id": t[3],
                        "receiver_id": t[4],
                        "payment_destination": t[6],
                        "transaction_id": t[7]
                    }
                    transaction_list.append(transaction_info)

            card_info["transactions"] = transaction_list
            card_list.append(card_info)

        return render_template('transactions.html', cards=card_list)

    except Exception as e:
        return f"Помилка: {e}", 500

@app.route('/exchange_rates')
def exchange_rates():
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM currency_conversion")
    currencies = cursor.fetchall()

    cursor.close()

    return render_template(
        'exchange_rates.html',
        currencies=currencies
    )

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if request.method == 'POST':
        receiver = request.form.get('receiver', '').replace(' ', '')  # Credit number of the receiver
        amount = request.form.get('amount', '')
        user_id = session.get('user_id')

        if not user_id:
            flash("Користувач не авторизований", 'error')
            return redirect(url_for('login'))

        try:
            cursor = mysql.connection.cursor()

            # Getting the client_id of the current user
            cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
            client = cursor.fetchone()
            if not client:
                flash("Клієнт не знайдений", 'error')
                return redirect(url_for('home_screen'))

            client_id = client[0]

            # Getting type 1 accounts
            cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
            accounts = cursor.fetchall()
            if not accounts:
                flash("Акаунти не знайдені", 'error')
                return redirect(url_for('home_screen'))

            account_ids = [account[0] for account in accounts]

            # Obtaining card accounts
            cursor.execute("""
                SELECT card_account_id, credit_number, my_money, sum, credit_limit, exporation_date, cvv_code, card_type
                FROM card_account WHERE account_id IN %s
            """, (tuple(account_ids),))
            cards = cursor.fetchall()

            if not cards:
                return redirect(url_for('creating_card'))

            card_list = []
            for card in cards:
                card_info = {
                    "card_account_id": card[0],
                    "credit_number": card[1],
                    "my_money": card[2],
                    "sum": card[3],
                    "credit_limit": card[4],
                    "exporation_date": card[5],
                    "cvv_code": card[6]
                }
                card_list.append(card_info)

            # Checking the recipient's receipt in the database
            cursor.execute("SELECT account_id FROM card_account WHERE credit_number = %s", (receiver,))
            receiver_account = cursor.fetchone()

            if receiver_account:
                receiver_account_id = receiver_account[0]

                # Getting the recipient's client_id
                cursor.execute("SELECT client_id FROM account WHERE account_id = %s", (receiver_account_id,))
                receiver_client = cursor.fetchone()

                if receiver_client:
                    receiver_client_id = receiver_client[0]

                    # Obtaining recipient data
                    cursor.execute("SELECT surname, name, patronymic FROM client WHERE client_id = %s", (receiver_client_id,))
                    receiver_info = cursor.fetchone()

                    if receiver_info:
                        receiver_full_name = f"{receiver_info[0]} {receiver_info[1]} {receiver_info[2]}"
                    else:
                        receiver_full_name = ""
                else:
                    receiver_full_name = ""
            else:
                receiver_full_name = ""

            return render_template('transfer_screen.html',
                                   cards=card_list,
                                   receiver=receiver,
                                   amount=amount,
                                   receiver_name=receiver_full_name)

        except Exception as e:
            flash(f"Помилка: {e}", 'error')
            return redirect(url_for('transfer'))

    return render_template('transfer_screen.html')

@app.route('/check_and_pay', methods=['GET', 'POST'])
def check_and_pay():
    if request.method == 'POST':
        card_number = request.form.get('card_number')
        receiver_card = request.form.get('receiver_card').replace(' ', '')
        sum = request.form.get('sum')
        payment_destination = request.form.get('payment_destination')
        user_id = session.get('user_id')
        if not user_id:
            return "Користувач не авторизований", 401
        cursor = mysql.connection.cursor()

        cursor.execute("SELECT surname, name, patronymic FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            return "Клієнт не знайдений", 404

        sender_name = f"{client[0]} {client[1]} {client[2]}"
        # Checking the existence of a recipient in the database
        cursor.execute("SELECT account_id FROM card_account WHERE credit_number = %s", (receiver_card,))
        receiver_account = cursor.fetchone()

        receiver_full_name = "Невідомий отримувач"
        if receiver_account:
            receiver_account_id = receiver_account[0]

            # Getting the recipient's client_id
            cursor.execute("SELECT client_id FROM account WHERE account_id = %s", (receiver_account_id,))
            receiver_client = cursor.fetchone()

            if receiver_client:
                receiver_client_id = receiver_client[0]

                # Obtaining recipient data
                cursor.execute("SELECT surname, name, patronymic FROM client WHERE client_id = %s",
                               (receiver_client_id,))
                receiver_info = cursor.fetchone()

                if receiver_info:
                    receiver_full_name = f"{receiver_info[0]} {receiver_info[1]} {receiver_info[2]}"
                else:
                    receiver_full_name = "Невідомий отримувач"
            else:
                receiver_full_name = "Невідомий отримувач"
        else:
            receiver_full_name = "Невідомий отримувач"

    return render_template('check_and_pay_screen.html', card_number=card_number, receiver_card=receiver_card, sum=sum, payment_destination=payment_destination, sender_name=sender_name, receiver_full_name=receiver_full_name)

@app.route('/refill_phone', methods=['GET', 'POST'])
def refill_phone():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number', '')
        phone_sum = request.form.get('phone_sum', '')
        user_id = session.get('user_id')
        if not user_id:
            flash("Користувач не авторизований", 'error')
            return redirect(url_for('login'))
        try:
            cursor = mysql.connection.cursor()

            # Getting client_id from the client table
            cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
            client = cursor.fetchone()
            if not client:
                flash("Клієнт не знайдений", 'error')
                return redirect(url_for('home_screen'))

            client_id = client[0]

            # Getting type 1 accounts from the account table
            cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
            accounts = cursor.fetchall()

            if not accounts:
                flash("Акаунти не знайдені", 'error')
                return redirect(url_for('home_screen'))

            account_ids = [account[0] for account in accounts]

            # Getting information about card accounts from the card_account table
            cursor.execute("""
                        SELECT card_account_id, credit_number, my_money, sum, credit_limit, exporation_date, cvv_code, card_type
                        FROM card_account WHERE account_id = %s
                    """, (tuple(account_ids),))
            cards = cursor.fetchall()

            if not cards:
                return redirect(url_for('creating_card'))

            card_list = []
            for card in cards:
                card_info = {
                    "card_account_id": card[0],
                    "credit_number": card[1],
                    "my_money": card[2],
                    "sum": card[3],
                    "credit_limit": card[4],
                    "exporation_date": card[5],
                    "cvv_code": card[6]
                }
                card_list.append(card_info)

            return render_template('refill_phone_screen.html', cards=card_list, phone_number=phone_number, phone_sum=phone_sum)

        except Exception as e:
            flash(f"Помилка: {e}", 'error')
            return redirect(url_for('refill_phone'))
    return render_template('refill_phone_screen.html')

@app.route('/create_refill_phone', methods=['GET', 'POST'])
def create_refill_phone():
    if request.method == 'POST':
        try:
            card_number = int(request.form.get('card_number'))
            phone_number = request.form.get('phone_number')
            sum_reffil = int(request.form.get('sum'))
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT curr_id FROM card_account WHERE card_account_id = %s",
                (card_number,)
            )
            curr_id = cursor.fetchone()
            if not curr_id:
                flash("Щось не так з валютою", 'error')
                return redirect(url_for('deposits'))

            cursor.execute(
                "SELECT payment_system_id FROM card_account WHERE card_account_id = %s",
                (card_number,)
            )
            payment_system_id = cursor.fetchone()

            if not payment_system_id:
                flash("Щось не так з платіжною системою", 'error')
                return redirect(url_for('deposits'))

            cursor.execute(
                "SELECT sum FROM card_account WHERE card_account_id = %s",
                (card_number,)
            )

            sum = cursor.fetchone()

            if not sum:
                flash("Щось не так з балансом", 'error')
                return redirect(url_for('refill_phone'))

            # Getting the rate for conversion into hryvnia
            cursor.execute(
                "SELECT sales_rate FROM currency_conversion WHERE currency_id = %s",
                (curr_id,)
            )
            conversion = cursor.fetchone()

            if not conversion:
                flash("Курс валют не знайдено", 'error')
                return redirect(url_for('refill_phone'))

            sales_rate = conversion[0]

            sum_uah = int(sum_reffil) / sales_rate

            if sum[0] < int(sum_uah):
                flash("На картці недостатньо коштів", 'error')
                return redirect(url_for('refill_phone'))

            # Card balance update
            cursor.execute(
                "UPDATE card_account SET sum = sum - %s WHERE card_account_id = %s",
                (sum_uah, card_number)
            )

            cursor.execute(
                "SELECT name FROM currency_conversion WHERE currency_id = %s",
                (curr_id,)
            )
            curr = cursor.fetchone()
            # Calling a method to create a transaction
            transaction_data = {
                "sum": sum_uah,
                "payer_id": card_number,
                "receiver_id": 0,
                "status": "Completed",
                "payment_system_id": payment_system_id[0],
                "currency": curr_id[0],
                "payment_destination": "Поповнення номеру телефона: " + phone_number + " на суму: " + str(f"{sum_uah:.3f}") + curr[0],
            }
            # Calling the function to create a transaction directly
            create_transaction_response = create_transaction_internal(transaction_data)
            if create_transaction_response.get("error"):
                raise Exception(create_transaction_response["error"])
            mysql.connection.commit()
            return redirect(url_for('home_screen'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Помилка : {e}", 'error')
            return redirect(url_for('refill_phone'))

    return redirect(url_for('home_screen'))

@app.route('/pay', methods=['GET', 'POST'])
def pay():
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401
    if request.method == 'POST':
        card_account = int(request.form.get('card_account'))  # ID card of the sender
        receiver_full_name = request.form.get('receiver_full_name')  # Recipient's full name
        receiver_card = request.form.get('receiver_card').replace(' ', '')
        destination = request.form.get('destination')  # Purpose of payment
        sum_uah = int(request.form.get('sum'))  # Amount in hryvnias
        try:
            cursor = mysql.connection.cursor()
            # Get sender's card details
            cursor.execute(
                "SELECT sum, curr_id FROM card_account WHERE card_account_id = %s", (card_account,)
            )
            sender_card = cursor.fetchone()
            if not sender_card:
                return "Картка відправника не знайдена", 404

            sender_balance, sender_currency = sender_card
            # Get the selling rate for the card currency
            cursor.execute(
                "SELECT buying_rate FROM currency_conversion WHERE currency_id = %s", (sender_currency,)
            )
            conversion_rate = cursor.fetchone()

            if not conversion_rate:
                return "Не знайдено курсу валют для картки", 400

            sales_rate = conversion_rate[0]

            # Calculation of the amount in the sender's currency
            sum_in_currency = sum_uah / sales_rate

            if sender_balance < sum_in_currency:
                return "Недостатньо коштів на рахунку", 400

            # Debiting funds from the sender's account
            cursor.execute(
                "UPDATE card_account SET sum = sum - %s WHERE card_account_id = %s",
                (sum_in_currency, card_account),
            )
            mysql.connection.commit()
            # Checking the recipient's card availability
            cursor.execute(
                "SELECT card_account_id, curr_id FROM card_account WHERE credit_number = %s",
                (receiver_card,)
            )
            receiver = cursor.fetchone()
            transaction_data = {
                "sum": sum_uah,
                "payer_id": card_account,
                "receiver_id": 0,
                "status": "Completed",
                "payment_system_id": 1,  # Default value
                "currency": 1,
                "payment_destination": destination,
            }
            if receiver:
                receiver_account_id, receiver_currency = receiver

                # Get the buying rate of the recipient's currency
                cursor.execute(
                    "SELECT sales_rate FROM currency_conversion WHERE currency_id = %s", (receiver_currency,)
                )
                receiver_conversion_rate = cursor.fetchone()

                if not receiver_conversion_rate:
                    return "Не знайдено курсу валют для отримувача", 400

                purchase_rate = receiver_conversion_rate[0]

                # Convert the amount to the recipient's currency
                sum_in_receiver_currency = int(sum_uah / purchase_rate)
                # Crediting funds to the recipient
                cursor.execute(
                    "UPDATE card_account SET sum = sum + %s WHERE card_account_id = %s",
                    (sum_in_receiver_currency, receiver_account_id),
                )
                cursor.execute(
                    "SELECT payment_system_id FROM card_account WHERE card_account_id = %s",
                    (receiver_account_id,)
                )
                payment_system_id = cursor.fetchone()

                transaction_data = {
                    "sum": sum_uah,
                    "payer_id": card_account,
                    "receiver_id": receiver_account_id,
                    "status": "Completed",
                    "payment_system_id": payment_system_id[0],  # Default value
                    "currency": 1,
                    "payment_destination": destination,
                }

            # Calling the function to create a transaction directly
            create_transaction_internal(transaction_data)
            mysql.connection.commit()
            cursor.close()

            return redirect(url_for('home_screen'))

        except Exception as e:
            mysql.connection.rollback()
            return f"Помилка: {e}", 500

    return render_template('check_and_pay_screen.html')

@app.route('/credit_history')
def credit_history():
    user_id = session.get('user_id')
    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()

    # Getting client_id from the client table
    cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
    client = cursor.fetchone()
    if not client:
        flash("Клієнт не знайдений", 'error')
        return redirect(url_for('home_screen'))

    client_id = client[0]
    cursor.execute("""SELECT c.sum, c.amount_repaid, c.status, c.credit_id
    FROM credit c
    WHERE client_id = %s AND status = %s""", (client_id, "Активний",))
    credits = cursor.fetchall()
    return render_template('credit_history.html', credits=credits)

@app.route('/credit_history_ar')
def credit_history_ar():
    user_id = session.get('user_id')
    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()

    # Getting client_id from the client table
    cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
    client = cursor.fetchone()
    if not client:
        flash("Клієнт не знайдений", 'error')
        return redirect(url_for('home_screen'))

    client_id = client[0]
    cursor.execute("""SELECT c.sum, c.amount_repaid, c.status, c.credit_id
    FROM credit c
    WHERE client_id = %s AND status = %s""", (client_id, "Закритий",))
    credits = cursor.fetchall()
    return render_template('credit_history_ar.html', credits=credits)

@app.route('/take_credit')
def take_credit():
    user_id = session.get('user_id')
    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('login'))
    try:
        cursor = mysql.connection.cursor()

        # Getting client_id from the client table
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            flash("Клієнт не знайдений", 'error')
            return redirect(url_for('home_screen'))

        client_id = client[0]

        # Getting type 1 accounts from the account table
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            flash("Акаунти не знайдені", 'error')
            return redirect(url_for('home_screen'))

        account_ids = [account[0] for account in accounts]

        # Getting information about card accounts from the card_account table
        cursor.execute("""
                    SELECT card_account_id, credit_number, my_money, sum, credit_limit, exporation_date, cvv_code, card_type
                    FROM card_account WHERE account_id = %s
                """, (tuple(account_ids),))
        cards = cursor.fetchall()

        if not cards:
            return redirect(url_for('creating_card'))

        card_list = []
        for card in cards:
            card_info = {
                "card_account_id": card[0],
                "credit_number": card[1],
                "my_money": card[2],
                "sum": card[3],
                "credit_limit": card[4],
                "exporation_date": card[5],
                "cvv_code": card[6]
            }
            card_list.append(card_info)

        return render_template('credit.html', cards=card_list)

    except Exception as e:
        flash(f"Помилка: {e}", 'error')
        return redirect(url_for('take_credit'))

@app.route('/credit', methods=['GET', 'POST'])
def credit():
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id:
            flash("Користувач не авторизований", 'error')
            return redirect(url_for('login'))

        cursor = mysql.connection.cursor()

        # Getting client_id from the client table
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            flash("Клієнт не знайдений", 'error')
            return redirect(url_for('home_screen'))

        client_id = client[0]
        sum = int(request.form.get('sum'))
        deadline = request.form.get('deadline')
        guarantor_surname = request.form.get('guarantor_surname')
        guarantor_name = request.form.get('guarantor_name')
        guarantor_patronymic = request.form.get('guarantor_patronymic')
        guarantor_address = request.form.get('guarantor_address')
        card_number = request.form.get('card_number')
        interest_rate = request.form.get('interest-rate')

        cursor.execute("SELECT sum FROM card_account WHERE card_account_id = %s", (card_number,))
        current_sum = cursor.fetchone()
        if not current_sum:
            flash("Щось не так з сумою", 'error')
            return redirect(url_for('take_credit'))


        # Inserting data into the quarantors table
        cursor.execute("""
            INSERT INTO quarantors (surname, `name`, patronymic, address)
            VALUES (%s, %s, %s, %s)
        """, (guarantor_surname, guarantor_name, guarantor_patronymic, guarantor_address))

        quarantor_id = cursor.lastrowid

        # Inserting data into the credit table
        cursor.execute("""
            INSERT INTO credit (client_id, sum, amount_repaid, payment_day, interest_rate, quarantor_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (client_id, sum, 0, deadline, interest_rate, quarantor_id, 'Активний'))
        credit_id = cursor.lastrowid

        cursor.execute("""SELECT curr_id FROM card_account WHERE card_account_id = %s""", (card_number,))
        curr_id = cursor.fetchone()

        cursor.execute(
            "SELECT sales_rate FROM currency_conversion WHERE currency_id = %s",
            (curr_id,)
        )
        conversion = cursor.fetchone()

        if not conversion:
            flash("Курс валют не знайдено", 'error')
            return redirect(url_for('deposits'))

        sales_rate = conversion[0]
        sum = sum/sales_rate
        # Card balance update
        new_sum = current_sum[0] + sum
        cursor.execute("UPDATE card_account SET sum = %s WHERE card_account_id = %s", (new_sum, card_number))
        cursor.execute("""SELECT payment_system_id FROM card_account WHERE card_account_id = %s""", (card_number,))
        payment_system_id = cursor.fetchone()

        transaction_data = {
            "sum": sum,
            "payer_id": 0,
            "receiver_id": card_number,
            "status": "Completed",
            "payment_system_id": payment_system_id[0],  # Default value
            "currency": curr_id[0],
            "payment_destination": "Надходження кредитних коштів за кредитом №" + str(credit_id)
        }
        # Calling the function to create a transaction directly
        create_transaction_response = create_transaction_internal(transaction_data)
        if create_transaction_response.get("error"):
            raise Exception(create_transaction_response["error"])

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('credit_history'))

    return redirect(url_for('home_screen'))

@app.route('/card_transaction', methods=['GET', 'POST'])
def card_transaction():
    card_number = request.args.get('card_number')
    card = card_number
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(""" SELECT card_account_id
        FROM card_account
        WHERE credit_number = %s""", (card_number,))
        card_number = cursor.fetchone()

        cursor.execute("""
                    SELECT t.sum, t.date, t.status, t.payer_id, t.receiver_id, t.currency, t.payment_destination, t.transaction_id
                    FROM transaction t
                    WHERE t.receiver_id = %s OR t.payer_id = %s
                    ORDER BY t.transaction_id DESC
                """, (card_number, card_number))

        transactions = cursor.fetchall()

        transaction_list = []

        for t in transactions:
            # If we send money to ourselves (payer_id = receiver_id), we add two transactions
            if t[3] == t[4]:
                # First transaction - receipt
                cursor.execute("""
                        SELECT c.name
                        FROM currency_conversion c
                        WHERE currency_id = %s""", (t[5],))
                currency_name = cursor.fetchone()
                currency_name = currency_name[0] if currency_name else "Невідома валюта"

                transaction_info = {
                    "sum": t[0],
                    "date": t[1],
                    "currency": currency_name,
                    "transaction_type": '+',
                    "status": t[2],
                    "payer_id": t[3],
                    "receiver_id": t[4],
                    "payment_destination": t[6],
                    "transaction_id": t[7]
                }
                transaction_list.append(transaction_info)

                transaction_info = {
                    "sum": t[0],
                    "date": t[1],
                    "currency": currency_name,
                    "transaction_type": '-',
                    "status": t[2],
                    "payer_id": t[3],
                    "receiver_id": t[4],
                    "payment_destination": t[6],
                    "transaction_id": t[7]
                }
                transaction_list.append(transaction_info)
            else:
                # If payer_id and receiver_id are different, add a regular transaction
                transaction_type = '+' if t[4] == card_number else '-'

                cursor.execute("""
                        SELECT c.name
                        FROM currency_conversion c
                        WHERE currency_id = %s""", (t[5],))
                currency_name = cursor.fetchone()
                currency_name = currency_name[0] if currency_name else "Невідома валюта"

                transaction_info = {
                    "sum": t[0],
                    "date": t[1],
                    "currency": currency_name,
                    "transaction_type": transaction_type,
                    "status": t[2],
                    "payer_id": t[3],
                    "receiver_id": t[4],
                    "payment_destination": t[6],
                    "transaction_id": t[7]
                }
                transaction_list.append(transaction_info)


        return render_template('card_transactions.html', card_number=card, transaction_list=transaction_list)
    except Exception as e:
        return f"Помилка: {e}", 500

@app.route('/pay_credit', methods=['GET', 'POST'])
def pay_credit():
    user_id = session.get('user_id')
    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()

    # Getting client_id from the client table
    cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
    client = cursor.fetchone()
    if not client:
        flash("Клієнт не знайдений", 'error')
        return redirect(url_for('home_screen'))

    client_id = client[0]
    cursor.execute("""SELECT c.credit_id, c.sum, c.amount_repaid, c.status
        FROM credit c
        WHERE client_id = %s AND status = %s""", (client_id, "Активний",))
    credits = cursor.fetchall()

    user_id = session.get('user_id')
    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('login'))
    try:
        cursor = mysql.connection.cursor()

        # Getting client_id from the client table
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            flash("Клієнт не знайдений", 'error')
            return redirect(url_for('home_screen'))

        client_id = client[0]

        # Getting type 1 accounts from the account table
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            flash("Акаунти не знайдені", 'error')
            return redirect(url_for('home_screen'))

        account_ids = [account[0] for account in accounts]

        # Getting information about card accounts from the card_account table
        cursor.execute("""
                            SELECT card_account_id, credit_number, my_money, sum, credit_limit, exporation_date, cvv_code, card_type
                            FROM card_account WHERE account_id = %s
                        """, (tuple(account_ids),))
        cards = cursor.fetchall()

        if not cards:
            return redirect(url_for('creating_card'))

        card_list = []
        for card in cards:
            card_info = {
                "card_account_id": card[0],
                "credit_number": card[1],
                "my_money": card[2],
                "sum": card[3],
                "credit_limit": card[4],
                "exporation_date": card[5],
                "cvv_code": card[6]
            }
            card_list.append(card_info)
    except Exception as e:
        flash(f"Помилка: {e}", 'error')
        return redirect(url_for('pay_credit'))

    return render_template('pay_credit.html', credit=credits, cards=card_list)

@app.route('/pay_for_credit', methods=['GET', 'POST'])
def pay_for_credit():
    if request.method == 'POST':
        try:
            # Getting data from a form
            card_id = request.form.get('card_number')  # Card ID
            credit_id = request.form.get('credit_id')  # Credit ID
            payment_sum = request.form.get('sum')  # Payment amount

            # Data conversion
            card_id = int(card_id)
            credit_id = int(credit_id)
            payment_sum_uah = int(payment_sum)

            # Add basic business logic (e.g., debiting a card and repaying a loan)
            cursor = mysql.connection.cursor()

            cursor.execute(
                "SELECT curr_id FROM card_account WHERE card_account_id = %s",
                (card_id,)
            )
            curr_id = cursor.fetchone()

            cursor.execute(
                "SELECT payment_system_id FROM card_account WHERE card_account_id = %s",
                (card_id,)
            )
            payment_system_id = cursor.fetchone()

            # Checking card balance
            cursor.execute("SELECT sum FROM card_account WHERE card_account_id = %s", (card_id,))
            card_balance = cursor.fetchone()
            if not card_balance:
                flash("Картка не знайдена.", "error")
                return redirect(url_for('home_screen'))

            cursor.execute(
                "SELECT buying_rate FROM currency_conversion WHERE currency_id = %s",
                (curr_id,)
            )
            conversion = cursor.fetchone()
            buyint_rate = conversion[0]

            payment_sum = payment_sum_uah / buyint_rate
            if card_balance[0] < payment_sum:
                flash("Недостатньо коштів на рахунку.", "error")
                return redirect(url_for('pay_credit'))

            # Debiting funds from the card
            cursor.execute(
                "UPDATE card_account SET sum = sum - %s WHERE card_account_id = %s",
                (payment_sum, card_id)
            )

            # Credit renewal
            cursor.execute(
                "UPDATE credit SET amount_repaid = amount_repaid + %s WHERE credit_id = %s",
                (payment_sum_uah, credit_id)
            )
            transaction_data = {
                "sum": payment_sum,
                "payer_id": card_id,
                "receiver_id": 0,
                "status": "Completed",
                "payment_system_id": payment_system_id[0],
                "currency": curr_id[0],
                "payment_destination": "Погашення кредиту № " + str(credit_id),
            }

            create_transaction_response = create_transaction_internal(transaction_data)
            if create_transaction_response.get("error"):
                raise Exception(create_transaction_response["error"])

            cursor.execute("""SELECT sum, amount_repaid FROM credit WHERE credit_id = %s""",(credit_id,))
            credit = cursor.fetchone()

            if credit[0] <= credit[1]:
                cursor.execute(
                    "UPDATE credit SET status = %s WHERE credit_id = %s",
                    ("Закритий", credit_id)
                )

            mysql.connection.commit()
            cursor.close()

            flash("Кредит успішно погашено.", "success")
            return redirect(url_for('credit_history'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Помилка: {str(e)}", "error")
            return redirect(url_for('pay_credit'))

    # For the GET method, we return the form
    return render_template('credit_history.html')

@app.route('/transaction_pdf/<transaction_id>')
def transaction_pdf(transaction_id):
    transaction_data = get_transaction_data(transaction_id)

    html_content = render_template('transaction_template.html', transaction=transaction_data)

    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdfkit.from_string(html_content, temp_pdf.name, configuration=config)

        temp_pdf.seek(0)

        filename = f"transaction_{transaction_id}.pdf"

        return send_file(
            temp_pdf.name,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

def get_transaction_data(transaction_id):
    try:
        # Getting a connection to the base
        cursor = mysql.connection.cursor()

        # Execute a query to get the transaction by transaction_id
        cursor.execute("""
            SELECT transaction_id, sum, date, payer_id, receiver_id, status, 
                   payment_destination, payment_system_id, currency 
            FROM transaction 
            WHERE transaction_id = %s
        """, (transaction_id,))

        # Getting the result
        transaction = cursor.fetchone()

        # If the transaction is not found
        if transaction is None:
            return {"error": "Транзакцію не знайдено"}

        cursor.execute("""SELECT name FROM payment_systems WHERE payment_system_id = %s""", (transaction[7],))
        payment_system = cursor.fetchone()[0]

        cursor.execute("""SELECT name FROM currency_conversion WHERE currency_id = %s""", (transaction[8],))
        curr_id = cursor.fetchone()[0]

        payer_id = "Невідомий"
        if transaction[3] == 0:
            payer_id = "єБанк"
        if transaction[3] != 0:
            cursor.execute("""SELECT account_id FROM card_account WHERE card_account_id = %s""", (transaction[3],))
            payer = cursor.fetchone()[0]
            if payer:
                cursor.execute("""SELECT client_id FROM account WHERE account_id = %s""", (payer,))
                client_id = cursor.fetchone()[0]
                cursor.execute("""SELECT surname, name, patronymic FROM client WHERE client_id = %s""", (client_id,))
                snp = cursor.fetchone()
                payer_id = str(snp[0]) + ' ' + str(snp[1]) + ' ' + str(snp[2])

        receiver_id = "Невідомий"
        if transaction[4] == 0:
            receiver_id = "єБанк"
        if transaction[4] != 0:
            cursor.execute("""SELECT account_id FROM card_account WHERE card_account_id = %s""", (transaction[4],))
            receiver = cursor.fetchone()[0]
            if receiver:
                cursor.execute("""SELECT client_id FROM account WHERE account_id = %s""", (receiver,))
                client_id = cursor.fetchone()[0]
                cursor.execute("""SELECT surname, name, patronymic FROM client WHERE client_id = %s""", (client_id,))
                snp = cursor.fetchone()
                receiver_id = str(snp[0]) + ' ' + str(snp[1]) + ' ' + str(snp[2])
        # We form a dictionary with the obtained data
        transaction_data = {
            "transaction_id": transaction[0],
            "sum": transaction[1],
            "date": transaction[2],
            "payer_id": payer_id,
            "receiver_id": receiver_id,
            "status": transaction[5],
            "payment_destination": transaction[6],
            "payment_system_id": payment_system,
            "currency": curr_id
        }

        return transaction_data

    except Exception as e:
        return {"error": str(e)}

@app.route('/generate_statement/<int:card_id>', methods=['POST'])
def generate_statement(card_id):
    # Get data for the last 30 days
    transactions_data = get_transactions_last_30_days(card_id)

    transactions = transactions_data["transactions"]
    start_date = transactions_data["start_date"].strftime("%Y-%m-%d")
    end_date = transactions_data["end_date"].strftime("%Y-%m-%d")


    user_id = session.get('user_id')

    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT surname, name, patronymic FROM client WHERE user_id =  %s""", (user_id,))
    snp = cursor.fetchone()

    cursor.execute("""SELECT curr_id FROM card_account WHERE card_account_id = %s""", (card_id,))
    curr_id = cursor.fetchone()[0]

    cursor.execute("""SELECT name FROM currency_conversion WHERE currency_id = %s""", (curr_id,))
    curr = cursor.fetchone()[0]

    cursor.execute("""SELECT sum FROM card_account WHERE card_account_id = %s""", (card_id,))
    sum = cursor.fetchone()[0]

    cursor.execute("""SELECT credit_number FROM card_account WHERE card_account_id = %s""", (card_id,))
    credit_number = cursor.fetchone()[0]

    cursor.execute("""SELECT payment_system_id FROM card_account WHERE card_account_id = %s""", (card_id,))
    payment_system_id = cursor.fetchone()[0]

    cursor.execute("""SELECT name FROM payment_systems WHERE payment_system_id = %s""", (payment_system_id,))
    payment_system = cursor.fetchone()[0]
    # Render the HTML template
    html_content = render_template(
        'transactions_list_pdf.html',
        transactions=transactions,
        start_date=start_date,
        end_date=end_date,
        snp=snp,
        curr=curr,
        sum=sum,
        credit_number=credit_number,
        payment_system=payment_system,
    )

    # Generate PDF
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdfkit.from_string(html_content, temp_pdf.name, configuration=config)
        temp_pdf.seek(0)
        filename = f"transaction_{card_id}_{start_date}_{end_date}.pdf"
        return send_file(
            temp_pdf.name,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

def get_transactions_last_30_days(card_id):
    try:
        cursor = mysql.connection.cursor()

        # Define the date range for the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        cursor.execute("""
            SELECT transaction_id, date, sum, payer_id, receiver_id, 
                   payment_destination, payment_system_id, currency, status
            FROM transaction
            WHERE (date BETWEEN %s AND %s) AND (payer_id = %s OR receiver_id = %s)
        """, (start_date, end_date, card_id, card_id))

        transactions = cursor.fetchall()

        result = []
        # Process each transaction
        for transaction in transactions:
            # Get payment system name
            cursor.execute("SELECT name FROM payment_systems WHERE payment_system_id = %s", (transaction[6],))
            payment_system_row = cursor.fetchone()
            payment_system = payment_system_row[0] if payment_system_row else "Unknown"

            # Get currency name
            cursor.execute("SELECT name FROM currency_conversion WHERE currency_id = %s", (transaction[7],))
            currency_row = cursor.fetchone()
            currency = currency_row[0] if currency_row else "Unknown"

            transaction_type = '-' if transaction[3] == card_id else '+'
            # Add result
            result.append({
                "transaction_id": transaction[0],
                "date": transaction[1],
                "sum": transaction[2],
                "payer_id": transaction[3],
                "receiver_id": transaction[4],
                "destination": transaction[5],
                "payment_system": payment_system,
                "currency": currency,
                "status": transaction[8],
                "type": transaction_type,
            })

        # Return successful result
        return {"transactions": result, "start_date": start_date, "end_date": end_date}

    except Exception as e:
        # Handle any errors
        return {"error": str(e), "transactions": [], "start_date": start_date, "end_date": end_date}

@app.route('/credit_info/<credit_id>')
def credit_info(credit_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()

    cursor.execute("""SELECT c.sum, c.amount_repaid, c.status, c.credit_id, c.interest_rate, c.status, c.payment_day, c.quarantor_id
        FROM credit c
        WHERE credit_id = %s""", (credit_id,))
    credit = cursor.fetchone()

    cursor.execute("""SELECT q.surname, q.name, q.patronymic, q.address FROM quarantors q WHERE quarantor_id = %s""", (credit[7],))
    guarantor = cursor.fetchone()
    return render_template('take_a_credit.html', credit=credit, guarantor=guarantor)

@app.route('/credit_pdf/<int:credit_id>', methods=['POST'])
def credit_pdf(credit_id):
    user_id = session.get('user_id')

    if not user_id:
        flash("Користувач не авторизований", 'error')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT surname, name, patronymic FROM client WHERE user_id =  %s""", (user_id,))
    snp = cursor.fetchone()

    cursor.execute("""SELECT payment_day FROM credit WHERE credit_id = %s""", (credit_id,))
    end_date = cursor.fetchone()[0].strftime("%Y-%m-%d")

    cursor.execute("""SELECT sum, amount_repaid, interest_rate FROM credit WHERE credit_id = %s""", (credit_id,))
    credit = cursor.fetchone()

    cursor.execute("""
                SELECT date, sum, status, currency
                FROM transaction
                WHERE payment_destination = %s
            """, (("Погашення кредиту № " + str(credit_id)),))

    transactions = cursor.fetchall()

    html_content = render_template(
        'credit_pdf.html',
        snp=snp,
        end_date=end_date,
        credit_id=credit_id,
        credit=credit,
        transactions=transactions,
    )

    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdfkit.from_string(html_content, temp_pdf.name, configuration=config)
        temp_pdf.seek(0)
        filename = f"credit_{credit_id}.pdf"
        return send_file(
            temp_pdf.name,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

if __name__ == '__main__':
    app.run(debug=True)
