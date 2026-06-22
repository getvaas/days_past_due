**Fuente**: conversación directa con el usuario

## Solicitud original

> "necesitamos una ultima historia, y tiene que ver con la creacion de un batch derivado desde esta lambda. Se lanzara un batch cuando el registro en el CSV supere los 5K registros? Este cantidad se definira en una variable de entorno... que tambien va a tener que estar creada en la carga de variables. Acordate que necesitamos llenar las variabes de entorno para uso local en el .env.example"

## Clarificaciones obtenidas

- **Servicio de batch**: AWS Batch
- **Respuesta SNS**: La Lambda no publica — el batch publica la respuesta cuando termina
