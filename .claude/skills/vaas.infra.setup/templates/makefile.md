# Template: Makefile

Shortcuts para los comandos de Terraform. Se coloca en la raíz del proyecto.

## Template

```makefile
.PHONY: all

LOCATION=deploy/terraform

ENV?=dev

help:
	@echo "Execute: make <plan|apply> ENV=<(dev)|stg|prod>"

plan:
	cd $(LOCATION) && \
	rm -rf .terraform* && \
	terraform init -backend-config=configuration/$(ENV)/backend.conf \
	  -backend-config=configuration/$(ENV)/profile.tfvars && \
	terraform plan \
	  -var-file=configuration/$(ENV)/vars.tfvars \
	  -var-file=configuration/global.tfvars \
	  -var-file=configuration/$(ENV)/profile.tfvars

apply:
	cd $(LOCATION) && \
	rm -rf .terraform* && \
	terraform init -backend-config=configuration/$(ENV)/backend.conf \
	  -backend-config=configuration/$(ENV)/profile.tfvars && \
	terraform apply \
	  -var-file=configuration/$(ENV)/vars.tfvars \
	  -var-file=configuration/global.tfvars \
	  -var-file=configuration/$(ENV)/profile.tfvars

clean:
	cd $(LOCATION) && \
	rm -rf .terraform*

just-plan:
	cd $(LOCATION) && \
	terraform plan \
	  -var-file=configuration/$(ENV)/vars.tfvars \
	  -var-file=configuration/global.tfvars \
	  -var-file=configuration/$(ENV)/profile.tfvars
```

## Uso

```bash
make plan ENV=dev      # Ver cambios en dev (default)
make plan ENV=stg      # Ver cambios en staging
make plan ENV=prod     # Ver cambios en producción
make apply ENV=dev     # Aplicar cambios en dev
make clean             # Limpiar archivos temporales de Terraform
make just-plan ENV=dev # Plan sin re-init (más rápido si ya inicializaste)
```
