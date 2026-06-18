# Conceptos Básicos de Terraform para Developers de Vaas

Este documento explica los conceptos mínimos de Terraform que un developer necesita saber para trabajar con la infraestructura de Vaas. No necesitas ser experto en Terraform — las skills generan todo el código por ti.

---

## ¿Qué es Terraform?

Terraform es una herramienta de **Infrastructure as Code (IaC)**. En vez de crear recursos en AWS manualmente desde la consola web, describes lo que necesitas en archivos `.tf` y Terraform se encarga de crearlo, actualizarlo o eliminarlo.

---

## Conceptos clave

### Module
Un **módulo** es un conjunto de archivos `.tf` que crean un grupo de recursos relacionados. En Vaas usamos módulos del repo `tf_modules` para crear cosas como servicios ECS, buckets S3, colas SQS, etc.

```hcl
module "my_service" {
  source = "git@github.com:getvaas/tf_modules.git//ecs_service"
  # Los parámetros del módulo van aquí
  environment      = "dev"
  ecs_service_name = "dev-my-service"
}
```

### Variable (`var.`)
Las **variables** son parámetros de entrada. Se definen en `inputs.tf` y sus valores se pasan desde archivos `.tfvars`.

```hcl
# inputs.tf — definición
variable "environment" {
  type = string
}

# vars.tfvars — valor
environment = "dev"

# Uso en código
resource "..." {
  name = var.environment   # → "dev"
}
```

### Local (`local.`)
Los **locals** son valores computados internos. Se definen en `locals.tf` y se usan para organizar configuración.

```hcl
# locals.tf
locals {
  service_name = "${var.environment}-my-service"
}

# Uso
module "ecs" {
  ecs_service_name = local.service_name   # → "dev-my-service"
}
```

### Provider
El **provider** configura la conexión a AWS (región, credenciales, tags por defecto).

### Backend
El **backend** es donde Terraform guarda su "state" — un archivo que recuerda qué recursos existen. En Vaas usamos S3 + DynamoDB para esto.

### State
El **state** es el archivo que Terraform usa para saber qué recursos ya creó. Vive en S3 y es compartido por el equipo. **Nunca lo edites manualmente.**

---

## Comandos que vas a usar

Solo necesitas 3 comandos, todos via Makefile:

```bash
make plan ENV=dev      # Ver qué cambios se harían (NO aplica nada)
make apply ENV=dev     # Aplicar los cambios (CREA/MODIFICA recursos en AWS)
make clean             # Limpiar archivos temporales
```

### `make plan` — Vista previa (seguro)
Muestra qué recursos se crearían, modificarían o eliminarían. **No hace cambios reales**. Siempre ejecuta plan antes de apply.

Ejemplo de output:
```
+ module.s3.aws_s3_bucket.bucket           # Se va a CREAR
~ module.ecs.aws_ecs_service.service       # Se va a MODIFICAR
- module.old.aws_sqs_queue.queue           # Se va a ELIMINAR

Plan: 1 to add, 1 to change, 1 to destroy.
```

### `make apply` — Aplicar cambios (cuidado)
Aplica los cambios mostrados en el plan. Terraform te pedirá confirmación antes de ejecutar.

**⚠️ IMPORTANTE**: Siempre revisa el plan antes de aplicar. Especialmente en `prod`.

---

## Archivos que vas a ver

| Archivo | Qué hace | ¿Lo edito? |
|---------|----------|------------|
| `main.tf` | Orquesta todos los módulos | Sí, para agregar/modificar módulos |
| `inputs.tf` | Define variables de entrada | Sí, cuando agregas nuevas variables |
| `locals.tf` | Configuración computada | Sí, para configurar módulos |
| `vars.tfvars` | Valores por ambiente | Sí, para cambiar valores por env |
| `global.tfvars` | Valores compartidos | Raramente |
| `backend.conf` | Config del state S3 | Solo al crear el proyecto |
| `Makefile` | Shortcuts de comandos | Raramente |

---

## Flujo típico de trabajo

1. **Generar código** — Usa las skills de infra (`vaas.infra.setup`, `vaas.infra.add`)
2. **Revisar** — Lee los archivos generados para entender qué se va a crear
3. **Plan** — `make plan ENV=dev` para ver los cambios
4. **Apply** — `make apply ENV=dev` para crear los recursos
5. **Verificar** — Revisa en AWS Console que todo se creó correctamente
6. **Repetir para otros ambientes** — `make plan ENV=stg`, `make apply ENV=stg`, etc.

---

## Glosario rápido

| Término | Qué es |
|---------|--------|
| **ECS** | Elastic Container Service — ejecuta contenedores Docker en AWS |
| **ECS Service** | Un servicio que corre containers 24/7 (tu API) |
| **ECS Task** | Una ejecución de container one-off o programada (un cron job) |
| **ECR** | Elastic Container Registry — donde se guardan las imágenes Docker |
| **ALB** | Application Load Balancer — distribuye tráfico HTTP/HTTPS |
| **Target Group** | Grupo de contenedores que reciben tráfico del ALB |
| **Listener Rule** | Regla que decide qué target group recibe cada request (por path, host, etc.) |
| **S3** | Simple Storage Service — almacenamiento de archivos |
| **SQS** | Simple Queue Service — cola de mensajes |
| **SNS** | Simple Notification Service — topic de pub/sub |
| **DLQ** | Dead Letter Queue — cola donde van los mensajes que fallaron |
| **IAM** | Identity and Access Management — permisos y roles |
| **Parameter Store** | Almacén de configuración en SSM (no-secretos) |
| **Secrets Manager** | Almacén de secretos (passwords, API keys) |
| **CloudWatch** | Servicio de logs y métricas |
| **Capacity Provider** | Configuración de instancias EC2 para el cluster ECS |
| **VPC** | Virtual Private Cloud — red privada en AWS |
| **Subnet** | Subdivisión de la VPC |
| **Security Group** | Firewall virtual para controlar tráfico |
