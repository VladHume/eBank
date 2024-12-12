from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from datetime import datetime

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
    return render_template('creating_account_screen.html')


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

    return render_template('create_account_screen.html')


@app.route('/home_screen')
def home_screen():
    return render_template('home_screen.html')


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
        taxpayer_card_id = request.form.get('taxpayer card id')

        cursor = mysql.connection.cursor()

        cursor.execute("SELECT client_id FROM client WHERE user_id = %s", (user_id,))
        client = cursor.fetchone()

        if not client:
            flash('Клієнт не знайдений', 'error')
            return redirect(url_for('update_info'))

        client_id = client[0]

        cursor.execute("""
            SELECT COUNT(*) FROM client
            WHERE (phone_number = %s OR passport_id = %s OR email = %s OR taxpayer_card_id = %s)
            AND client_id != %s
        """, (phone_number, passport_id, email, taxpayer_card_id, client_id))

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
                    passport_id = %s, address = %s, email = %s, taxpayer_card_id = %s
                WHERE client_id = %s
            """
            cursor.execute(sql_client, (surname, name, patronymic, phone_number, passport_id, address, email, taxpayer_card_id, client_id))

            mysql.connection.commit()
            flash('Дані успішно оновлено', 'success')
            return redirect(url_for('client_cabinet'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Упс, сталася помилка', 'error')
            return redirect(url_for('update_info'))
        finally:
            cursor.close()

    return render_template('update_account_info.html')



if __name__ == '__main__':
    app.run(debug=True)
