-- Resultado por cuota: lo que se escribió en la tabla.
SELECT
    borrower_contract_id   AS contract,
    borrower_installment_reference AS inst,
    `date`                 AS due_date,
    gross_amount           AS gross,
    dpd_current,
    dpd_max,
    amount_in_arrears      AS arrears
FROM scheduled_payments_installments
WHERE company_code = 42
ORDER BY borrower_contract_id, `date`;

-- Resumen por contrato (DPD actual del crédito).
SELECT borrower_contract_id, MAX(dpd_current) AS dpd_credito
FROM scheduled_payments_installments
WHERE company_code = 42
GROUP BY borrower_contract_id
ORDER BY dpd_credito DESC, borrower_contract_id;

-- Resumen histórico (mayor mora alcanzada).
SELECT borrower_contract_id, MAX(dpd_max) AS max_tiempo_mora
FROM scheduled_payments_installments
WHERE company_code = 42
GROUP BY borrower_contract_id
ORDER BY max_tiempo_mora DESC, borrower_contract_id;
