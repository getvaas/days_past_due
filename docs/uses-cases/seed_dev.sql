-- =============================================================================
-- Seed data casos de prueba — payments_db (dev)
-- company_id = 86 | Corte de referencia: 2026-10-03
-- Casos: docs/uses-cases/cases.md
-- =============================================================================

-- Limpiar datos previos (descomentar si es necesario):
-- DELETE FROM payment_tape WHERE company_id = 86;
-- DELETE FROM scheduled_payments_installments WHERE company_id = 86;

-- ─── CASO 1: Happy path ───────────────────────────────────────────────────────
-- Todas las cuotas pagadas completas y en fecha

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-1', '2026-06-01', 1000.00),
(86, '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-2', '2026-07-01', 1000.00),
(86, '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-3', '2026-08-01', 1000.00),
(86, '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-4', '2026-09-01', 1000.00),
(86, '6603dce6-6b76-c0dc-96c1-08ddb5d9c44e', 'REF-5', '2026-10-01', 1000.00);

-- ─── CASO 2: Pago parcial en la última cuota ──────────────────────────────────
-- Jun-Sep completos, Oct solo 500

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-1', '2026-06-01', 1000.00),
(86, 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-2', '2026-07-01', 1000.00),
(86, 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-3', '2026-08-01', 1000.00),
(86, 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-4', '2026-09-01', 1000.00),
(86, 'a8f3c92d-4e71-b8a5-91c2-09efb6e1d772', 'REF-5', '2026-10-01',  500.00);

-- ─── CASO 3: Sin pagos registrados ───────────────────────────────────────────
-- 4 cuotas vencidas, sin ningún pago

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', 'c4d9e1f7-2b86-a3c5-84d1-15a7c8b9e334', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'c4d9e1f7-2b86-a3c5-84d1-15a7c8b9e334', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'c4d9e1f7-2b86-a3c5-84d1-15a7c8b9e334', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'c4d9e1f7-2b86-a3c5-84d1-15a7c8b9e334', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0);

-- (sin payment_tape)

-- ─── CASO 4: Pago atrasado ya regularizado ────────────────────────────────────
-- Ago pagado 15 días tarde, resto en fecha

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-1', '2026-06-01', 1000.00),
(86, '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-2', '2026-07-01', 1000.00),
(86, '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-3', '2026-08-16', 1000.00),
(86, '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-4', '2026-09-01', 1000.00),
(86, '7e2b4a91-9f53-c7d8-a2e4-23bc4d6f8125', 'REF-5', '2026-10-01', 1000.00);

-- ─── CASO 5: Pago parcial en cuota intermedia ─────────────────────────────────
-- Ago pagado solo 500, resto completos

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-1', '2026-06-01', 1000.00),
(86, 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-2', '2026-07-01', 1000.00),
(86, 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-3', '2026-08-01',  500.00),
(86, 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-4', '2026-09-01', 1000.00),
(86, 'f1a7c3e8-5d94-b6f2-83a1-47d9e2b1c948', 'REF-5', '2026-10-01', 1000.00);

-- ─── CASO 6: Pago anticipado de cuotas ───────────────────────────────────────
-- Jun, Jul, Ago pagados en junio por adelantado

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-1', '2026-06-01', 1000.00),
(86, '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-2', '2026-06-01', 1000.00),
(86, '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-3', '2026-06-01', 1000.00),
(86, '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-4', '2026-09-01', 1000.00),
(86, '2b8d5e1c-7a42-d9b3-c0e7-58f2a1c3b674', 'REF-5', '2026-10-01', 1000.00);

-- ─── CASO 7: Sobrepago en una cuota ───────────────────────────────────────────
-- Oct pagado con 1500 (500 de excedente)

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-1', '2026-06-01', 1000.00),
(86, '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-2', '2026-07-01', 1000.00),
(86, '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-3', '2026-08-01', 1000.00),
(86, '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-4', '2026-09-01', 1000.00),
(86, '9c4e7b23-3f81-a5d6-b9e2-67d4e8a1f583', 'REF-5', '2026-10-01', 1500.00);

-- ─── CASO 8: Múltiples cuotas con pago parcial ────────────────────────────────
-- Ago, Sep, Oct pagados al 50%

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-1', '2026-06-01', 1000.00),
(86, '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-2', '2026-07-01', 1000.00),
(86, '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-3', '2026-08-01',  500.00),
(86, '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-4', '2026-09-01',  500.00),
(86, '5a1f8d6e-2c93-b4a7-c5d9-71e3b9c2d847', 'REF-5', '2026-10-01',  500.00);

-- ─── CASO 9: Pago en exceso que cubre cuota siguiente ─────────────────────────
-- Sep paga 1500 (cubre Sep + mitad de Oct), Oct sin pago

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-1', '2026-06-01', 1000.00),
(86, 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-2', '2026-07-01', 1000.00),
(86, 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-3', '2026-08-01', 1000.00),
(86, 'd3e9b4a1-6f57-c8b2-a4f1-82a5c1d9e673', 'REF-4', '2026-09-01', 1500.00);

-- ─── CASO 10: Cuota pagada en dos partes ──────────────────────────────────────
-- Oct: dos pagos de 500 en días distintos

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-1', '2026-06-01', 1000.00),
(86, '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-2', '2026-07-01', 1000.00),
(86, '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-3', '2026-08-01', 1000.00),
(86, '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-4', '2026-09-01', 1000.00),
(86, '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-5', '2026-10-01',  500.00),
(86, '8b2c5e9f-4a76-d1b3-e7c4-93b6e2f1c594', 'REF-5', '2026-10-02',  500.00);

-- ─── CASO 11: Mora prolongada con pago parcial reciente ───────────────────────
-- Jun-Ago sin pago, Sep paga solo la cuota de Jun, Oct sin pago

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '0e7f3a8b-1c64-b9d5-c2a8-04e1c3b8d456', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '0e7f3a8b-1c64-b9d5-c2a8-04e1c3b8d456', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '0e7f3a8b-1c64-b9d5-c2a8-04e1c3b8d456', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '0e7f3a8b-1c64-b9d5-c2a8-04e1c3b8d456', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '0e7f3a8b-1c64-b9d5-c2a8-04e1c3b8d456', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '0e7f3a8b-1c64-b9d5-c2a8-04e1c3b8d456', 'REF-1', '2026-09-01', 1000.00);

-- ─── CASO 12: Pago el mismo día del corte ─────────────────────────────────────
-- Oct pagado el 2026-10-03 (día exacto del corte)

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-1', '2026-06-01', 1000.00),
(86, '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-2', '2026-07-01', 1000.00),
(86, '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-3', '2026-08-01', 1000.00),
(86, '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-4', '2026-09-01', 1000.00),
(86, '4f6a9c2d-8b35-e1f7-d3b9-15c8e4a2b167', 'REF-5', '2026-10-03', 1000.00);

-- ─── CASO 13: Diferencia de centavos por redondeo ─────────────────────────────
-- Oct pagado con 999.50 (falta $0.50)

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-1', '2026-06-01', 1000.00),
(86, '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-2', '2026-07-01', 1000.00),
(86, '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-3', '2026-08-01', 1000.00),
(86, '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-4', '2026-09-01', 1000.00),
(86, '1a5e8b3c-9d27-f4a6-b8e1-26d9f5c3a278', 'REF-5', '2026-10-01',  999.50);

-- ─── CASO 14: Crédito reestructurado ──────────────────────────────────────────
-- Ago eliminado, Sep y Oct con nuevo monto de 800

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '6c2d7f1b-5e94-a3c8-f6d2-37e1a4b8c389', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '6c2d7f1b-5e94-a3c8-f6d2-37e1a4b8c389', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '6c2d7f1b-5e94-a3c8-f6d2-37e1a4b8c389', 'REF-3', '2026-09-01',  800.00,  800.00, 0, 0, 0, 0),
(86, '86', '6c2d7f1b-5e94-a3c8-f6d2-37e1a4b8c389', 'REF-4', '2026-10-01',  800.00,  800.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '6c2d7f1b-5e94-a3c8-f6d2-37e1a4b8c389', 'REF-1', '2026-06-01', 1000.00),
(86, '6c2d7f1b-5e94-a3c8-f6d2-37e1a4b8c389', 'REF-2', '2026-07-01', 1000.00),
(86, '6c2d7f1b-5e94-a3c8-f6d2-37e1a4b8c389', 'REF-3', '2026-09-01',  800.00),
(86, '6c2d7f1b-5e94-a3c8-f6d2-37e1a4b8c389', 'REF-4', '2026-10-01',  800.00);

-- ─── CASO 15: Pago duplicado ───────────────────────────────────────────────────
-- Ago pagado dos veces

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-1', '2026-06-01', 1000.00),
(86, 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-2', '2026-07-01', 1000.00),
(86, 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-3', '2026-08-01', 1000.00),
(86, 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-3', '2026-08-01', 1000.00),
(86, 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-4', '2026-09-01', 1000.00),
(86, 'b8e1c4a6-3f78-d2b5-a7c9-48f2b6d1e493', 'REF-5', '2026-10-01', 1000.00);

-- ─── CASO 16: Primera cuota nunca pagada ──────────────────────────────────────
-- Jun sin pago, Jul-Oct pagados completos

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-2', '2026-07-01', 1000.00),
(86, '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-3', '2026-08-01', 1000.00),
(86, '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-4', '2026-09-01', 1000.00),
(86, '3d9a6e2f-7b51-c4d8-b3e5-59a3c7e2f1a4', 'REF-5', '2026-10-01', 1000.00);

-- ─── CASO 17: Contrato sin payment tape ───────────────────────────────────────
-- Solo cuotas, cero pagos

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', 'e7b3f1c8-2a64-b5d9-c1f7-6ab4d8c1f2b5', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'e7b3f1c8-2a64-b5d9-c1f7-6ab4d8c1f2b5', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'e7b3f1c8-2a64-b5d9-c1f7-6ab4d8c1f2b5', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', 'e7b3f1c8-2a64-b5d9-c1f7-6ab4d8c1f2b5', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0);

-- (sin payment_tape)

-- ─── CASO 18: Pagos normales y luego abandono ─────────────────────────────────
-- Jun-Ago pagados, Sep-Oct sin pago

INSERT INTO scheduled_payments_installments (company_id, company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount, principal_amount, interest_amount, guarantee_amount, tax_amount, fee_amount) VALUES
(86, '86', '4a8c2b9e-7f31-d6c4-b5e9-58c3a7d1e924', 'REF-1', '2026-06-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '4a8c2b9e-7f31-d6c4-b5e9-58c3a7d1e924', 'REF-2', '2026-07-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '4a8c2b9e-7f31-d6c4-b5e9-58c3a7d1e924', 'REF-3', '2026-08-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '4a8c2b9e-7f31-d6c4-b5e9-58c3a7d1e924', 'REF-4', '2026-09-01', 1000.00, 1000.00, 0, 0, 0, 0),
(86, '86', '4a8c2b9e-7f31-d6c4-b5e9-58c3a7d1e924', 'REF-5', '2026-10-01', 1000.00, 1000.00, 0, 0, 0, 0);

INSERT INTO payment_tape (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment) VALUES
(86, '4a8c2b9e-7f31-d6c4-b5e9-58c3a7d1e924', 'REF-1', '2026-06-01', 1000.00),
(86, '4a8c2b9e-7f31-d6c4-b5e9-58c3a7d1e924', 'REF-2', '2026-07-01', 1000.00),
(86, '4a8c2b9e-7f31-d6c4-b5e9-58c3a7d1e924', 'REF-3', '2026-08-01', 1000.00);
