# Banking Web App

## Project Overview
This is a simple banking web application backend implemented with **Flask** and **MySQL**. It provides user registration and authentication, client and account management, card creation, transactions, deposits, credits, and PDF generation for transactions/credit statements using **pdfkit** and **wkhtmltopdf**.

## Main Features
- User registration and login.
- Client profile and account creation.
- Card management (create/delete cards, generate unique card numbers and CVV).
- Viewing transactions, generating transaction PDFs and monthly statements.
- Deposits and credits (take/repay).
- Phone refills and internal money transfers.
- Exchange rate handling (currency conversion tables in DB).

## Requirements
- Python 3.8+
- Flask
- flask-mysqldb
- pdfkit
- wkhtmltopdf (system binary)
- MySQL server

## Configuration
In `app.py` you need to configure:
- Flask `SECRET_KEY`
- MySQL connection:
  ```py
  app.config['MYSQL_HOST'] = 'localhost'
  app.config['MYSQL_USER'] = 'root'
  app.config['MYSQL_PASSWORD'] = 'password'
  app.config['MYSQL_DB'] = 'banksystem'
  ```
- `wkhtmltopdf` path for `pdfkit.configuration`, e.g.:
  ```py
  config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
  ```

## Database
Recommended tables used by the app (inferred from code):
- `users` — stores login/password.
- `client` — client personal data (surname, name, patronymic, phone_number, passport_id, email, taxpayer_card_id, user_id).
- `account`, `card_account` — account and card details (balances, currency, card numbers).
- `transaction` — transaction history used for statements and logs.
- `currency_conversion`, `payment_systems`, `card_types`, `deposits`, `credit`, `quarantors`.
The app runs many SELECT / INSERT / UPDATE / DELETE queries; consult `app.py` for exact fields and logic.

## Important Routes
- `/` → redirects to `/login`
- `/register`, `/add_client` → register client
- `/login_user` → POST login
- `/creating_card` → create new card (generates unique credit number and CVV)
- `/transactions` → view transactions
- `/transaction_pdf/<transaction_id>` → download a transaction PDF
- `/generate_statement/<card_id>` → generates a 30‑day statement PDF
- `/deposits`, `/take_deposit` → deposit operations
- `/credit`, `/take_credit`, `/pay_for_credit` → credit operations  

## Running the App
1. Ensure MySQL and wkhtmltopdf are installed and configured.
2. Run the app:
```bash
python app.py
```
By default it runs in debug mode (`app.run(debug=True)` in `app.py`). 
