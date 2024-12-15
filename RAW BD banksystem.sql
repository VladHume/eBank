CREATE SCHEMA banksystem 
DEFAULT CHARACTER SET cp1251 -- кодування
COLLATE cp1251_ukrainian_ci; -- правила пошуку 
USE banksystem;
-- спочатку створення усіх таблиць

CREATE TABLE client (
-- імя	 		тип_даних	додаткові атрибути	
	client_id	INTEGER NOT NULL AUTO_INCREMENT,
    surname		VARCHAR(50),
    `name`		VARCHAR(50),
    patronymic	VARCHAR(50),
    phone_number	VARCHAR(15),
    passport_id VARCHAR(10),
    address VARCHAR(50),
    email VARCHAR(50),
	taxpayer_card_id VARCHAR(10),
    user_id	INTEGER,
    PRIMARY KEY(client_id),
    CONSTRAINT UC_client UNIQUE (phone_number,passport_id, email)
);

CREATE TABLE account (
  account_id INT NOT NULL AUTO_INCREMENT,
  status VARCHAR(45) ,
  client_id INT ,
  account_type INT,
  opening_date DATETIME ,
  closing_date DATETIME ,
  account_limit INT ,
  PRIMARY KEY (account_id)
  );

CREATE TABLE card_account(
	card_account_id	INT NOT NULL AUTO_INCREMENT,
	account_id		INT,
	credit_number 	VARCHAR(16),
	card_type	INT,
    payment_system_id INT,
	sum INT,
	my_money INT,
	exporation_date DATETIME,
	cvv_code VARCHAR(3),
	credit_limit INT,
	curr_id INT,
    pin VARCHAR(4),
	PRIMARY KEY (card_account_id)	
);

CREATE TABLE currency_conversion(
	currency_id INT NOT NULL AUTO_INCREMENT,
	`name` VARCHAR(50),
	buying_rate INT,
	sales_rate INT,
	PRIMARY KEY(currency_id)
);

CREATE TABLE transaction(
	transaction_id  INT NOT NULL AUTO_INCREMENT,
	sum INT,
	date DATE,
	payer_id INT,
	receiver_id INT,
	status VARCHAR(50),
	payment_system_id INT,
	currency INT,
	PRIMARY KEY(transaction_id)
);

CREATE TABLE payment_systems(
	payment_system_id INT NOT NULL AUTO_INCREMENT,
	`name` VARCHAR(50),
	PRIMARY KEY(payment_system_id)
);

CREATE TABLE private(
	private_id  INT NOT NULL AUTO_INCREMENT,
	account_id INT,
	balance INT,
	PRIMARY KEY(private_id)
);

CREATE TABLE business(
	business_id INT NOT NULL AUTO_INCREMENT,
	account_id INT,
	balance INT,
	business_name VARCHAR(50),
	account_manager_id INT,
	PRIMARY KEY(business_id)
);

CREATE TABLE managers(
	manager_id INT NOT NULL AUTO_INCREMENT,
	surname		VARCHAR(50),
    `name`		VARCHAR(50),
    patronymic	VARCHAR(50),
	PRIMARY KEY(manager_id)
);

CREATE TABLE quarantors(
	quarantor_id INT NOT NULL AUTO_INCREMENT,
	surname		VARCHAR(50),
    `name`		VARCHAR(50),
    patronymic	VARCHAR(50),
	address VARCHAR(50),
	PRIMARY KEY(quarantor_id)
);

CREATE TABLE credit(
	credit_id  INT NOT NULL AUTO_INCREMENT,
	client_id INT,
	sum INT,
	payment_day	DATETIME,
	interest_rate VARCHAR(50), -- не зрозуміло який тип для стовпця
	quarantor_id INT,
	status VARCHAR(50),
	currency INT,
	PRIMARY KEY(credit_id)
);

CREATE TABLE credit_history(
	credit_history_id INT NOT NULL AUTO_INCREMENT,
	client_id	INT,
    credit_id	INT,
    payment_day	DATETIME,
	amount_repaid INT,
	status VARCHAR(50),
	PRIMARY KEY(credit_history_id)
);
CREATE TABLE credit_limit_history(
	limit_id INT NOT NULL AUTO_INCREMENT,
	limit_amount INT,
	card_account_id INT,
	change_date DATETIME,
	reason TEXT,
	PRIMARY KEY(limit_id)
);

CREATE TABLE card_types(
	card_type_id  INT NOT NULL AUTO_INCREMENT,
	type VARCHAR(50),
	PRIMARY KEY(card_type_id)
);


CREATE TABLE deposits(
	deposit_id INT NOT NULL AUTO_INCREMENT,
	client_id INT,
	account INT,
	opening_date DATETIME,
	closing_date DATETIME,
	interest_rate VARCHAR(50),
	status VARCHAR(50),
	currency INT,
	PRIMARY KEY(deposit_id)
);

CREATE TABLE users(
	user_id INT NOT NULL AUTO_INCREMENT,
	password VARCHAR(100),
	login VARCHAR(50),
	UNIQUE(login),
	PRIMARY KEY(user_id)
);

CREATE TABLE notification(
	notification_id INT NOT NULL AUTO_INCREMENT,
	user_id INT,
	message TEXT,
	date_sent DATETIME,
	notification_type INT,
	PRIMARY KEY(notification_id)
);

CREATE TABLE notification_type(
	notification_type_id INT NOT NULL AUTO_INCREMENT,
	type VARCHAR(50),
	PRIMARY KEY(notification_type_id)
);

CREATE TABLE account_types(
	account_type_id INT NOT NULL AUTO_INCREMENT,
	type VARCHAR(50),
	PRIMARY KEY(account_type_id)
);

-- Додавання зовнішніх ключів
USE banksystem;
-- account
ALTER TABLE account
ADD CONSTRAINT FK_AccountClient FOREIGN KEY (client_id) REFERENCES client (client_id) ON DELETE CASCADE;
ALTER TABLE account
ADD CONSTRAINT FK_AccountAcctypes FOREIGN KEY (account_type) REFERENCES account_types (account_type_id);


-- card_account
ALTER TABLE card_account
ADD CONSTRAINT FK_CAccountAccount FOREIGN KEY (account_id) REFERENCES account (account_id)  ON DELETE CASCADE;
ALTER TABLE card_account
ADD CONSTRAINT FK_CAccountCType FOREIGN KEY (card_type) REFERENCES card_types (card_type_id);
ALTER TABLE card_account
ADD CONSTRAINT FK_CAccountCurrency FOREIGN KEY (curr_id )REFERENCES currency_conversion (currency_id) ON DELETE SET NULL;

-- client
ALTER TABLE client
ADD CONSTRAINT FK_ClientUser FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE;


-- credit
ALTER TABLE credit
ADD CONSTRAINT FK_CreditGuarantor FOREIGN KEY (quarantor_id) REFERENCES quarantors (quarantor_id)  ON DELETE SET NULL;
ALTER TABLE credit
ADD CONSTRAINT FK_CreditCurrency FOREIGN KEY (currency) REFERENCES currency_conversion (currency_id) ON DELETE SET NULL;
ALTER TABLE credit
ADD CONSTRAINT FK_CreditClient FOREIGN KEY (client_id) REFERENCES client (client_id); -- ON DELETE SET NULL;

-- credit_history
ALTER TABLE credit_history
ADD CONSTRAINT FK_CreditHClient FOREIGN KEY (client_id) REFERENCES client (client_id)  ON DELETE CASCADE;
ALTER TABLE credit_history
ADD CONSTRAINT FK_CreditHCredit FOREIGN KEY (credit_id) REFERENCES credit (credit_id) ON DELETE CASCADE;

-- credit_limit_history
ALTER TABLE credit_limit_history
ADD CONSTRAINT FK_CreditLHCAccount FOREIGN KEY (card_account_id) REFERENCES card_account (card_account_id)  ON DELETE CASCADE;

-- deposits
ALTER TABLE deposits
ADD CONSTRAINT FK_DepoisitsCard FOREIGN KEY (client_id) REFERENCES client (client_id) ON DELETE CASCADE;
ALTER TABLE deposits
ADD CONSTRAINT FK_DepoisitsCurr FOREIGN KEY (currency) REFERENCES currency_conversion (currency_id) ON DELETE SET NULL;



-- notification
ALTER TABLE notification
ADD CONSTRAINT FK_NotifUser FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE;
ALTER TABLE notification
ADD CONSTRAINT FK_NotifNotifType FOREIGN KEY (notification_type) REFERENCES notification_type (notification_type_id) ON DELETE CASCADE;

-- private
ALTER TABLE private
ADD CONSTRAINT FK_PrivateAccount FOREIGN KEY (account_id) REFERENCES account (account_id)  ON DELETE CASCADE;

-- business
ALTER TABLE business
ADD CONSTRAINT FK_BussinessAccount FOREIGN KEY (account_id)REFERENCES account (account_id)  ON DELETE CASCADE;
ALTER TABLE business
ADD CONSTRAINT FK_BussinessManager FOREIGN KEY (account_manager_id) REFERENCES managers (manager_id) ON DELETE SET NULL;

-- transaction
ALTER TABLE transaction
ADD CONSTRAINT FK_TransPayers FOREIGN KEY (payer_id) REFERENCES card_account (card_account_id) ON DELETE CASCADE;
ALTER TABLE transaction
ADD CONSTRAINT FK_TransReciever FOREIGN KEY (receiver_id) REFERENCES card_account (card_account_id) ON DELETE CASCADE;
ALTER TABLE transaction
ADD CONSTRAINT FK_TransPaySys FOREIGN KEY (payment_system_id) REFERENCES payment_systems (payment_system_id) ON DELETE SET NULL;
ALTER TABLE transaction
ADD CONSTRAINT FK_TransCurr FOREIGN KEY (currency) REFERENCES currency_conversion (currency_id) ON DELETE SET NULL; 

INSERT INTO card_types (type)
VALUES
    ('Дебетова'),
    ('Кредитна');

INSERT INTO payment_systems (`name`)
VALUES
    ('Visa'),
    ('MasterCard');

INSERT INTO currency_conversion (`name`, buying_rate, sales_rate)
VALUES
    ('UAH', 1, 1),
    ('USD', 27, 28),
    ('EUR', 30, 31);

INSERT INTO account_types (type)
VALUES
    ('Приватний'),
    ('Бізнес');