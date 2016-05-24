CREATE TABLE last_lookup (
    phone VARCHAR(30) PRIMARY KEY,
    ticker VARCHAR(30) NOT NULL
);

CREATE TABLE scheduled_sends (
    phone VARCHAR(30) NOT NULL,
    ticker VARCHAR(30) NOT NULL,
    send_time VARCHAR(30) NOT NULL,
    sent INT(11) DEFAULT 0,
    active INT(11) DEFAULT 1,
    PRIMARY KEY (phone, ticker, send_time)
)