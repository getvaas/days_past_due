-- Fixtures para integración. Calculation date asumida: 2026-05-04.
-- company_id = 42 en todos los casos.
--
-- Días esperados desde calc_date=2026-05-04:
--   2026-02-01 → 92
--   2026-03-01 → 64
--   2026-04-01 → 33
--
-- Escenarios:
--   C001 — todas las cuotas pagadas exactamente en fecha.
--   C002 — cuotas 1 y 3 pagadas; 2 sin pago. Modo join vs cascade difieren:
--          join: inst 2 mora=64; inst 3 paid (porque tiene installment_ref).
--          cascade: pool=2000 cubre inst 1+2; inst 3 queda sin pool (mora=33).
--   C003 — pago parcial 500 / 1000. Cambia con --partial-counts en cascade.
--   C004 — sin pagos.
--   C005 (cascade-only) — un solo pago de 1500 cubre cuota 1 (1000) y deja 500
--          en cuota 2 (parcial); con --partial-counts inst 2 marcaría como pagada.

INSERT INTO scheduled_payments_installments
    (company_code, borrower_contract_id, borrower_installment_reference, `date`, gross_amount,
     guarantee_amount, principal_amount, interest_amount, tax_amount, fee_amount)
VALUES
    -- C001: totalmente pagado
    (42, 'C001', 'C001-1', '2026-02-01', 1000, 0, 800, 150, 30, 20),
    (42, 'C001', 'C001-2', '2026-03-01', 1000, 0, 800, 150, 30, 20),
    (42, 'C001', 'C001-3', '2026-04-01', 1000, 0, 800, 150, 30, 20),

    -- C002: cuota 2 sin pago
    (42, 'C002', 'C002-1', '2026-02-01', 1000, 0, 800, 150, 30, 20),
    (42, 'C002', 'C002-2', '2026-03-01', 1000, 0, 800, 150, 30, 20),
    (42, 'C002', 'C002-3', '2026-04-01', 1000, 0, 800, 150, 30, 20),

    -- C003: pago parcial en cuota 1
    (42, 'C003', 'C003-1', '2026-02-01', 1000, 0, 800, 150, 30, 20),

    -- C004: sin pagos
    (42, 'C004', 'C004-1', '2026-04-01', 1000, 0, 800, 150, 30, 20),

    -- C005: pago overflow (cascade)
    (42, 'C005', 'C005-1', '2026-03-01', 1000, 0, 800, 150, 30, 20),
    (42, 'C005', 'C005-2', '2026-04-01', 1000, 0, 800, 150, 30, 20);

INSERT INTO payment_tape
    (company_id, borrower_contract_id, borrower_installment_reference, payment_date, total_payment)
VALUES
    -- C001
    (42, 'C001', 'C001-1', '2026-02-01', 1000),
    (42, 'C001', 'C001-2', '2026-03-01', 1000),
    (42, 'C001', 'C001-3', '2026-04-01', 1000),

    -- C002 (cuotas 1 y 3 pagadas; 2 sin pago)
    (42, 'C002', 'C002-1', '2026-02-01', 1000),
    (42, 'C002', 'C002-3', '2026-04-01', 1000),

    -- C003 (parcial)
    (42, 'C003', 'C003-1', '2026-02-01', 500),

    -- C004: sin pagos

    -- C005: un único pago de 1500
    (42, 'C005', 'C005-1', '2026-03-01', 1500);
