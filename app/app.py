
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from datetime import datetime
import random

app = Flask(__name__)

app.config['SECRET_KEY'] = '1234'
# Конфігурація MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'новий_пароль'
app.config['MYSQL_DB'] = 'banksystem'

mysql = MySQL(app)

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

        # Отримання client_id з таблиці client
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            return "Клієнт не знайдений", 404

        client_id = client[0]

        # Отримання акаунтів типу 1 з таблиці account
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            return "Акаунти не знайдені", 404

        account_ids = [account[0] for account in accounts]

        # Отримання інформації про карткові акаунти з таблиці card_account
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

            # Отримання типу картки за card_type_id
            cursor.execute("SELECT type FROM card_types WHERE card_type_id = %s", (card[7],))
            card_type = cursor.fetchone()
            if card_type:
                card_info["card_type"] = card_type[0]
            else:
                card_info["card_type"] = "Невідомий тип"  # Якщо тип не знайдено

            card_list.append(card_info)

        return render_template('card_info.html', cards=card_list)
    except Exception as e:
        return f"Помилка: {e}", 500

def generate_credit_card(payment_system):
    # Перші цифри визначаються платіжною системою
    prefix = '4' if payment_system == 1 else '5'
    # Генеруємо номер картки (16 цифр)
    credit_number = prefix + ''.join(str(random.randint(0, 9)) for _ in range(15))
    # Генеруємо CVV (3 цифри)
    cvv = ''.join(str(random.randint(0, 9)) for _ in range(3))
    return credit_number, cvv

def generate_unique_credit_card(cursor, payment_system):
    while True:
        # Генерація номера картки та CVV
        card_number, cvv = generate_credit_card(payment_system)

        # Перевірка унікальності номера картки в БД
        cursor.execute("SELECT COUNT(*) FROM card_account WHERE credit_number = %s", (card_number,))
        if cursor.fetchone()[0] == 0:
            return card_number, cvv

@app.route('/creating_card', methods=['GET', 'POST'])
def creating_card():
    user_id = session.get('user_id')
    if not user_id:
        return "Користувач не авторизований", 401

    if request.method == 'POST':
        card_type = int(request.form['card_type'])  # Тип картки: 1 - дебетова, 2 - кредитна
        payment_system = int(request.form['payment_system'])  # 1 - VISA, 2 - MasterCard
        currency = int(request.form['currency'])  # Валюта (curr_id)
        pin = request.form['PIN']  # PIN-код

        cursor = mysql.connection.cursor()

        # Генерація унікального номера картки та CVV
        credit_number, cvv_code = generate_unique_credit_card(cursor, payment_system)

        # Встановлення кредитного ліміту залежно від типу картки
        credit_limit = 0 if card_type == 1 else 20000

        # Отримання client_id
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client_id = cursor.fetchone()
        if not client_id:
            return "Клієнт не знайдений", 404

        # Отримання account_id
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id[0],))
        account_id = cursor.fetchone()
        if not account_id:
            return "Акаунт не знайдений", 404

        # Додавання запису в card_account
        cursor.execute("""
            INSERT INTO card_account (
                account_id, card_type, payment_system_id, sum, my_money, exporation_date, cvv_code, credit_limit, curr_id, pin, credit_number
            )
            VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL 3 YEAR, %s, %s, %s, %s, %s)
        """, (account_id[0], card_type, payment_system, 0, 0, cvv_code, credit_limit, currency, pin, credit_number))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('home_screen'))

    # Якщо GET-запит, отримуємо дані для вибору типів карток, платіжних систем і валют
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

        # Перевіряємо, чи картка належить поточному користувачеві
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

        # Видаляємо картку
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

        # Отримання client_id з таблиці client
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            flash("Клієнт не знайдений", 'error')
            return redirect(url_for('home_screen'))

        client_id = client[0]

        # Отримання акаунтів типу 1 з таблиці account
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            flash("Акаунти не знайдені", 'error')
            return redirect(url_for('home_screen'))

        account_ids = [account[0] for account in accounts]

        # Отримання інформації про карткові акаунти з таблиці card_account
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

            # Отримання типу картки за card_type_id
            cursor.execute("SELECT type FROM card_types WHERE card_type_id = %s", (card[7],))
            card_type = cursor.fetchone()
            if card_type:
                card_info["card_type"] = card_type[0]
            else:
                card_info["card_type"] = "Невідомий тип"

            card_list.append(card_info)

        # Перевірка наявності депозиту
        cursor.execute("SELECT * FROM deposits WHERE client_id = %s", (client_id,))
        deposit = cursor.fetchone()

        if deposit:
            # Якщо депозит існує, передаємо його дані в шаблон
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

        # Отримання даних депозиту з форми
        credit_number = request.form.get('credit_number')
        opening_date = datetime.today()
        closing_date = request.form.get('closing_date')
        interest_rate = int(request.form.get('interest_rate'))
        deposit_amount = request.form.get('deposit-amount')
        # Отримання curr_id для картки
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

        # Отримання курсу для конвертації у гривні
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

        # Оновлення балансу картки
        cursor.execute(
            "UPDATE card_account SET sum = sum - %s WHERE card_account_id = %s",
            (deposit_amount, credit_number)
        )

        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        # Виклик методу для створення транзакції
        transaction_data = {
            "sum": deposit_amount,
            "payer_id": credit_number,
            "receiver_id": 0,
            "status": "Completed",
            "payment_system_id": payment_system_id[0],  # Значення за замовчуванням
            "currency": curr_id[0],
            "payment_destination": "Поповнення депозиту"
        }
        # Виклик функції для створення транзакції безпосередньо
        create_transaction_response = create_transaction_internal(transaction_data)
        if create_transaction_response.get("error"):
            raise Exception(create_transaction_response["error"])
        # Додавання депозиту в базу
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
        payment_destination =  data['payment_destination']

        # Перетворення типів для коректного внесення в базу
        sum = int(sum)
        payer_id = int(payer_id)
        receiver_id = int(receiver_id)
        payment_system_id = int(payment_system_id)
        currency = int(currency)

        # Поточна дата
        date = datetime.now().strftime('%Y-%m-%d')

        # Додавання транзакції в базу
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

        # Отримуємо client_id з таблиці client
        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()
        if not client:
            return "Клієнт не знайдений", 404

        client_id = client[0]

        # Отримуємо акаунти типу 1 з таблиці account
        cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
        accounts = cursor.fetchall()

        if not accounts:
            return "Акаунти не знайдені", 404

        account_ids = [account[0] for account in accounts]

        # Якщо account_ids містить лише одне значення, забезпечуємо це як кортеж
        if len(account_ids) == 1:
            account_ids = (account_ids[0],)  # робимо кортежем

        # Отримуємо інформацію по картам з таблиці card_account
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

            # Отримуємо тип картки
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
                # Якщо ми відправляємо гроші самому собі (payer_id = receiver_id), додаємо дві транзакції
                if t[3] == t[4]:
                    # Перша транзакція - надходження
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
                    # Якщо payer_id і receiver_id різні, додаємо звичайну транзакцію
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

            # Отримання client_id поточного користувача
            cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
            client = cursor.fetchone()
            if not client:
                flash("Клієнт не знайдений", 'error')
                return redirect(url_for('home_screen'))

            client_id = client[0]

            # Отримання акаунтів типу 1
            cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
            accounts = cursor.fetchall()
            if not accounts:
                flash("Акаунти не знайдені", 'error')
                return redirect(url_for('home_screen'))

            account_ids = [account[0] for account in accounts]

            # Отримання карткових акаунтів
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

            # Перевірка існування отримувача в базі даних
            cursor.execute("SELECT account_id FROM card_account WHERE credit_number = %s", (receiver,))
            receiver_account = cursor.fetchone()

            if receiver_account:
                receiver_account_id = receiver_account[0]

                # Отримання client_id отримувача
                cursor.execute("SELECT client_id FROM account WHERE account_id = %s", (receiver_account_id,))
                receiver_client = cursor.fetchone()

                if receiver_client:
                    receiver_client_id = receiver_client[0]

                    # Отримання даних отримувача
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
        # Перевірка існування отримувача в базі даних
        cursor.execute("SELECT account_id FROM card_account WHERE credit_number = %s", (receiver_card,))
        receiver_account = cursor.fetchone()

        receiver_full_name = "Невідомий отримувач"
        if receiver_account:
            receiver_account_id = receiver_account[0]

            # Отримання client_id отримувача
            cursor.execute("SELECT client_id FROM account WHERE account_id = %s", (receiver_account_id,))
            receiver_client = cursor.fetchone()

            if receiver_client:
                receiver_client_id = receiver_client[0]

                # Отримання даних отримувача
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

            # Отримання client_id з таблиці client
            cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
            client = cursor.fetchone()
            if not client:
                flash("Клієнт не знайдений", 'error')
                return redirect(url_for('home_screen'))

            client_id = client[0]

            # Отримання акаунтів типу 1 з таблиці account
            cursor.execute("SELECT account_id FROM account WHERE client_id = %s AND account_type = 1", (client_id,))
            accounts = cursor.fetchall()

            if not accounts:
                flash("Акаунти не знайдені", 'error')
                return redirect(url_for('home_screen'))

            account_ids = [account[0] for account in accounts]

            # Отримання інформації про карткові акаунти з таблиці card_account
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

            # Отримання курсу для конвертації у гривні
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

            # Оновлення балансу картки
            cursor.execute(
                "UPDATE card_account SET sum = sum - %s WHERE card_account_id = %s",
                (sum_uah, card_number)
            )

            cursor.execute(
                "SELECT name FROM currency_conversion WHERE currency_id = %s",
                (curr_id,)
            )
            curr = cursor.fetchone()
            # Виклик методу для створення транзакції
            transaction_data = {
                "sum": sum_uah,
                "payer_id": card_number,
                "receiver_id": 0,
                "status": "Completed",
                "payment_system_id": payment_system_id[0],
                "currency": curr_id[0],
                "payment_destination": "Поповнення номеру телефона: " + phone_number + " на суму: " + str(f"{sum_uah:.3f}") + curr[0],
            }
            # Виклик функції для створення транзакції безпосередньо
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
        card_account = int(request.form.get('card_account'))  # ID картки відправника
        receiver_full_name = request.form.get('receiver_full_name')  # ПІБ отримувача
        receiver_card = request.form.get('receiver_card').replace(' ', '')
        destination = request.form.get('destination')  # Призначення платежу
        sum_uah = int(request.form.get('sum'))  # Сума в гривнях
        try:
            cursor = mysql.connection.cursor()
            # Отримати дані картки відправника
            cursor.execute(
                "SELECT sum, curr_id FROM card_account WHERE card_account_id = %s", (card_account,)
            )
            sender_card = cursor.fetchone()
            if not sender_card:
                return "Картка відправника не знайдена", 404

            sender_balance, sender_currency = sender_card
            # Отримати курс продажу для валюти картки
            cursor.execute(
                "SELECT buying_rate FROM currency_conversion WHERE currency_id = %s", (sender_currency,)
            )
            conversion_rate = cursor.fetchone()

            if not conversion_rate:
                return "Не знайдено курсу валют для картки", 400

            sales_rate = conversion_rate[0]

            # Розрахунок суми в валюті відправника
            sum_in_currency = sum_uah / sales_rate

            if sender_balance < sum_in_currency:
                return "Недостатньо коштів на рахунку", 400

            # Списання коштів з рахунку відправника
            cursor.execute(
                "UPDATE card_account SET sum = sum - %s WHERE card_account_id = %s",
                (sum_in_currency, card_account),
            )
            mysql.connection.commit()
            # Перевірка наявності картки отримувача
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
                "payment_system_id": 1,  # Значення за замовчуванням
                "currency": 1,
                "payment_destination": destination,
            }
            if receiver:
                receiver_account_id, receiver_currency = receiver

                # Отримати курс купівлі валюти отримувача
                cursor.execute(
                    "SELECT sales_rate FROM currency_conversion WHERE currency_id = %s", (receiver_currency,)
                )
                receiver_conversion_rate = cursor.fetchone()

                if not receiver_conversion_rate:
                    return "Не знайдено курсу валют для отримувача", 400

                purchase_rate = receiver_conversion_rate[0]

                # Конвертувати суму в валюту отримувача
                sum_in_receiver_currency = int(sum_uah / purchase_rate)
                # Зарахування коштів отримувачу
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
                    "payment_system_id": payment_system_id[0],  # Значення за замовчуванням
                    "currency": 1,
                    "payment_destination": destination,
                }

            # Виклик функції для створення транзакції безпосередньо
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
    return render_template('credit_history.html')

@app.route('/take_credit')
def take_credit():
    return render_template('credit.html')

if __name__ == '__main__':
    app.run(debug=True)
