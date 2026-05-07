-- Subset de columnas suficiente para correr el job DPD (MySQL).
-- No es la tabla completa de prod — solo lo que las queries de dpd/ tocan.

DROP TABLE IF EXISTS scheduled_payments_installments;
DROP TABLE IF EXISTS payment_tape;

CREATE TABLE scheduled_payments_installments (
    id                              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    company_code                    INT    NOT NULL,
    borrower_contract_id            VARCHAR(64)  NOT NULL,
    borrower_installment_reference  VARCHAR(64)  NOT NULL,
    `date`                          DATE   NOT NULL,
    gross_amount                    DECIMAL(18,4) NOT NULL,
    guarantee_amount                DECIMAL(18,4) DEFAULT 0,
    principal_amount                DECIMAL(18,4) DEFAULT 0,
    interest_amount                 DECIMAL(18,4) DEFAULT 0,
    tax_amount                      DECIMAL(18,4) DEFAULT 0,
    fee_amount                      DECIMAL(18,4) DEFAULT 0,
    creation_date                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_update_date                TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_spi_company_contract (company_code, borrower_contract_id)
    -- dpd_current / dpd_max / amount_in_arrears las agrega migrations.py
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE payment_tape (
    id                              BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    company_id                      INT    NOT NULL,
    borrower_contract_id            VARCHAR(64) NOT NULL,
    borrower_installment_reference  VARCHAR(64),
    payment_date                    DATE   NOT NULL,
    total_payment                   DECIMAL(18,4) NOT NULL,
    creation_date                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pt_company_contract (company_id, borrower_contract_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
