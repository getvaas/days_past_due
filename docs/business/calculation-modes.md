# Modos de cálculo: join vs cascade

Cómo se asignan los pagos a las cuotas para decidir qué está pagado y qué está en mora. Hay dos modos, en
`dpd/modes/`. Ambos producen `{id, dpd_current, amount_in_arrears}` por cuota.

## Modo `join` — [dpd/modes/join_installment.py](../../dpd/modes/join_installment.py)

Une cada cuota con sus pagos por `borrower_installment_reference` y compara `SUM(total_payment)` contra
`gross_amount`.

- Una cuota está **paga** si `total_paid >= gross_amount × paid_threshold`.
- Pagos sin `borrower_installment_reference` se **ignoran** (no se pueden asignar a una cuota concreta).
- En SQL es un `LEFT JOIN` contra una subquery agregada por `(borrower_contract_id, borrower_installment_reference)`.
- Compatible con MySQL 5.7+ (sin CTEs).

## Modo `cascade` — [dpd/modes/cascade_fifo.py](../../dpd/modes/cascade_fifo.py)

FIFO por contrato: **todos** los pagos del contrato se acumulan en un pool y se drenan cuota por cuota en orden
de fecha. El excedente fluye a la cuota siguiente.

- Cuotas ordenadas por `(installment_date asc, id asc)`; pagos por `(payment_date asc, id asc)`.
- Orden de aplicación de buckets dentro de cada cuota:

  `guarantee → principal → interest → moratory_interest → tax → fee`

  `moratory_interest` no existe del lado SPI → siempre 0, pero se mantiene en el orden por consistencia con el spec.
- Una cuota está **paga** si `applied >= gross × paid_threshold`. Con `partial_payment_counts=True`, basta
  `applied > 0`.

## Diferencia clave (ejemplo del seed de tests)

Contrato `C002`: cuotas 1, 2, 3 de 1000 c/u. Se pagan la 1 y la 3 (con sus referencias), la 2 no.

| Modo | Resultado |
|------|-----------|
| `join` | Cuota 2 en mora; cuota 3 paga (tiene su `installment_reference`). |
| `cascade` | Pool = 2000 cubre cuotas 1 y 2 (orden de fecha); la 3 queda sin pool → en mora. |

→ **join** respeta a qué cuota se imputó el pago; **cascade** ignora la referencia y aplica por antigüedad.

## Parámetros que afectan el cálculo

Definidos en `RunConfig` ([dpd/config.py](../../dpd/config/config.py)):

| Parámetro | Default | Efecto |
|-----------|---------|--------|
| `grace_days` | 1 | Días de gracia restados antes de contar mora. |
| `paid_threshold` | 1.0 | Fracción de `gross` que debe cubrirse para considerar la cuota al día. |
| `partial_payment_counts` | False | Solo cascade: cualquier pago parcial (`applied > 0`) marca la cuota como paga. |

La función pura testeable es `compute_from_data(installments, payments, cfg)` en cada modo. Ver
[code/compute-conventions.md](../code/compute-conventions.md).
