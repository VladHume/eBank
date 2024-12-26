SET GLOBAL event_scheduler = ON;
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
    credit_limit_full INT DEFAULT 20000,
	credit_limit INT,
	curr_id INT,
    pin VARCHAR(4),
	PRIMARY KEY (card_account_id),
	CHECK (my_money >= 0),
    CHECK (credit_limit >= 0)
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
    payment_destination VARCHAR(200),
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
    amount_repaid INT,
	payment_day	DATETIME,
	interest_rate INT,
	quarantor_id INT,
	status VARCHAR(50),
	PRIMARY KEY(credit_id)
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
	opening_date DATETIME,
	closing_date DATETIME,
    amount INT,
	interest_rate VARCHAR(50),
	status VARCHAR(50),
	PRIMARY KEY(deposit_id)
);

CREATE TABLE users(
	user_id INT NOT NULL AUTO_INCREMENT,
	password VARCHAR(100),
	login VARCHAR(50),
	UNIQUE(login),
	PRIMARY KEY(user_id)
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
ADD CONSTRAINT FK_CreditClient FOREIGN KEY (client_id) REFERENCES client (client_id); -- ON DELETE SET NULL;

-- credit_limit_history
ALTER TABLE credit_limit_history
ADD CONSTRAINT FK_CreditLHCAccount FOREIGN KEY (card_account_id) REFERENCES card_account (card_account_id)  ON DELETE CASCADE;

-- deposits
ALTER TABLE deposits
ADD CONSTRAINT FK_DepoisitsCard FOREIGN KEY (client_id) REFERENCES client (client_id) ON DELETE CASCADE;

-- private
ALTER TABLE private
ADD CONSTRAINT FK_PrivateAccount FOREIGN KEY (account_id) REFERENCES account (account_id)  ON DELETE CASCADE;

-- transaction
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
    ('Приватний');


DELIMITER //
CREATE TRIGGER update_sum_on_change
BEFORE UPDATE ON card_account
FOR EACH ROW
BEGIN
    -- Коли значення поля `sum` зменшується (списання коштів)
    IF NEW.sum < OLD.sum THEN
        SET @withdraw_amount = OLD.sum - NEW.sum;

        -- Перевіряємо тип картки
        IF NEW.card_type = 1 THEN
            -- Дебетова картка: тільки списання з особистих коштів
            IF OLD.my_money >= @withdraw_amount THEN
                SET NEW.my_money = OLD.my_money - @withdraw_amount;
            END IF;
        ELSE
            -- Кредитна картка: списання з урахуванням кредитного ліміту
            IF OLD.my_money >= @withdraw_amount THEN
                SET NEW.my_money = OLD.my_money - @withdraw_amount; -- Зменшуємо лише особисті кошти
            ELSE
                -- Особистих коштів недостатньо
                SET NEW.my_money = 0; -- Власні кошти списуються повністю
                SET NEW.credit_limit = OLD.credit_limit - (@withdraw_amount - OLD.my_money); -- Зменшуємо кредитний ліміт

                -- Щоб кредитний ліміт не був від'ємним
                IF NEW.credit_limit < 0 THEN
                    SET NEW.credit_limit = 0;
                END IF;
            END IF;
        END IF;

    -- Коли значення поля `sum` збільшується (додавання коштів)
    ELSEIF NEW.sum > OLD.sum THEN
        SET @add_amount = NEW.sum - OLD.sum; -- Сума, яку потрібно додати

        -- Перевіряємо тип картки
        IF NEW.card_type = 1 THEN
            -- Дебетова картка: тільки додавання до особистих коштів
            SET NEW.my_money = OLD.my_money + @add_amount;
        ELSE
            -- Кредитна картка: обробка кредитного ліміту та особистих коштів
            SET @full_credit = NEW.credit_limit_full;

            -- Спершу погашаємо кредитний ліміт
            IF OLD.credit_limit < @full_credit THEN
                SET @credit_deficit = @full_credit - OLD.credit_limit; -- Скільки бракує до повного відновлення кредитного ліміту

                IF @add_amount <= @credit_deficit THEN
                    -- Повністю додаємо до кредитного ліміту
                    SET NEW.credit_limit = OLD.credit_limit + @add_amount;
                    SET @add_amount = 0;
                ELSE
                    -- Частково додаємо до кредитного ліміту, залишок додається до особистих коштів
                    SET NEW.credit_limit = @full_credit; -- Кредитний ліміт повністю відновлений
                    SET @add_amount = @add_amount - @credit_deficit;
                END IF;
            END IF;

            SET NEW.my_money = OLD.my_money + @add_amount;
        END IF;
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER update_sum_on_my_money_change
BEFORE UPDATE ON card_account
FOR EACH ROW
BEGIN
    -- Якщо змінюється my_money, оновлюємо поле sum
    IF NEW.my_money != OLD.my_money AND NEW.my_money >=0 THEN
        SET NEW.sum = NEW.my_money + NEW.credit_limit;
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER update_sum_on_credit_limit_change
BEFORE UPDATE ON card_account
FOR EACH ROW
BEGIN
    -- Якщо змінюється credit_limit, оновлюємо поле sum
    IF NEW.credit_limit != OLD.credit_limit AND NEW.credit_limit >=0 THEN
        SET NEW.sum = NEW.my_money + NEW.credit_limit;
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER insert_sum_on_credit_limit_change
BEFORE INSERT ON card_account
FOR EACH ROW
BEGIN
    -- Якщо змінюється credit_limit, оновлюємо поле sum
    IF NEW.sum = 0 THEN
        SET NEW.sum = NEW.my_money + NEW.credit_limit;
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER set_active_status
BEFORE INSERT ON deposits
FOR EACH ROW
BEGIN
    IF NEW.status IS NULL OR NEW.status = '' THEN
        SET NEW.status = 'active';
    END IF;
END //
DELIMITER ;


DELIMITER //
CREATE TRIGGER validate_insert_card_account_limit
BEFORE INSERT ON account
FOR EACH ROW
BEGIN
    IF NEW.account_limit > 10000000 AND NEW.account_type = 1  THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Для приватних осіб ліміт не може перевищувати 10000000';
    END IF;
END//
DELIMITER ;


DELIMITER //
CREATE TRIGGER prevent_delete_active_deposit
BEFORE DELETE ON deposits
FOR EACH ROW
BEGIN
    IF OLD.status = 'active' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Неможливо видалити активний депозит';
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER validate_card_account_insert
BEFORE INSERT ON card_account
FOR EACH ROW
BEGIN
    -- Перевірка на негативні значення
    IF NEW.sum < 0 OR NEW.my_money < 0 OR NEW.credit_limit < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Поле sum, my_money та credit_limit не можуть бути від\'ємними';
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE TRIGGER validate_card_account_update
BEFORE UPDATE ON card_account
FOR EACH ROW
BEGIN
    -- Перевірка на негативні значення
    IF NEW.sum < 0 OR NEW.my_money < 0 OR NEW.credit_limit < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Поле sum, my_money та credit_limit не можуть бути від\'ємними';
    END IF;
END//
DELIMITER ;

DELIMITER //
CREATE PROCEDURE calculate_year_interest()
BEGIN
    UPDATE deposits
    SET amount = CASE
        WHEN status = 'active' THEN amount + (amount * (CAST(interest_rate AS UNSIGNED) / 100))
        ELSE amount
    END;
END //
DELIMITER ;

DELIMITER //
CREATE EVENT year_update_interest_event
ON SCHEDULE EVERY 1 YEAR
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    -- Викликаємо процедуру для нарахування відсотків
    CALL calculate_interest();
END //
DELIMITER ;
