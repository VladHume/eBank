from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL

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
    return redirect(url_for('login'))


@app.route('/login')
def login():
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
            return redirect(url_for('creating_account_screen'))
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
        cursor.close()

        if user and user[1] == password:
            return render_template('home_screen.html', user=user)
        else:
            flash('Невірний логін або пароль', 'error')
            return redirect(url_for('index'))
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)
