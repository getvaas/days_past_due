# Glosario de dominio

Términos del negocio de morosidad (Days Past Due) usados en todo el código. Los nombres técnicos
(columnas, parámetros) se mantienen en inglés.

| Término | Definición |
|---------|------------|
| **Cuota** (*SPI*, `scheduled_payments_installments`) | Una fila por vencimiento programado de un crédito. Tiene `gross_amount` y su desglose en buckets (`principal`, `interest`, `guarantee`, `tax`, `fee`). |
| **Pago** (`payment_tape`) | Una fila por pago recibido, con `total_payment`. |
| **DPD** (Days Past Due) | Días calendario desde el vencimiento de una cuota impaga, menos los días de gracia. `dpd = max((calc_date − installment_date).days − grace_days, 0)`. |
| **`dpd_current`** | Máximo DPD entre las cuotas vencidas de un contrato a la fecha de corte. |
| **`dpd_max`** | High-watermark histórico: `max(dpd_max_previo, dpd_current)`. Se recupera del output del run anterior (S3). **Nunca decrece.** |
| **`amount_in_arrears`** | Suma de los montos adeudados (`gross − pagado`) en cuotas con `dpd > 0`. |
| **`grace_days`** | Días calendario de gracia tras el vencimiento antes de contar mora. Default **1**. |
| **`paid_threshold`** | Fracción mínima pagada para considerar una cuota "al día". Default `1.0` (100%). Ej. `0.8` = 80%. |
| **`rate_type`** | `"fixed"` o `"variable"`. En variable, el SPI debe cargarse manualmente (no hay generación automática). |
| **`borrower_contract_id`** | Identificador del crédito. Clave de unión entre cuotas y pagos. |
| **`borrower_installment_reference`** | Identificador de la cuota dentro del contrato. Clave del modo `join`. |
| **`key`** | Nombre de la columna del loan tape que identifica el contrato. Debe coincidir con `borrower_contract_id`. |
| **Loan tape** | DataFrame con una fila por contrato. Es lo que la Lambda enriquece con columnas de productos. |
| **Bucket** | Componente del `gross_amount` de una cuota: `principal`, `interest`, `guarantee`, `tax`, `fee` (+ `moratory_interest`, siempre 0 del lado SPI). |

## Filtro por compañía — dos columnas que NO coinciden

Cada tabla se filtra por su propia columna y los valores **no son iguales**:

| Tabla | Columna de filtro | Tipo | Ejemplo |
|-------|-------------------|------|---------|
| `payment_tape` | `company_id` | numérico | `86` |
| `scheduled_payments_installments` | `company_code` | string | `"sistecredito"` |

⚠ No se unen las tablas por compañía — se unen por `borrower_contract_id` (+ referencia de cuota en modo join).
`RunConfig` lleva ambos campos (`company_id` y `company_code`) por separado.

## Tasas de interés — dos fuentes distintas

Mezclarlas produce resultados incorrectos:

| Uso | Fuente | Descripción |
|-----|--------|-------------|
| **Generación de SPI** | Columna `interest_rate` del loan tape | Tasa por contrato (deudor). Usada por `spi_builder`. |
| **Cálculo de VPN** | `metadata.interest_rate` del mensaje SQS | Tasa del tranche (descuento del fondo). Usada por `products/vpn.py`. |

Ver [calculation-modes.md](calculation-modes.md) para los modos y [products.md](products.md) para los productos.
