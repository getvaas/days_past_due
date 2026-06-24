FROM public.ecr.aws/lambda/python:3.12

WORKDIR /var/task

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dpd/ ./dpd/

# Lambda entry point (Batch lo sobreescribe con --command en el job definition)
CMD ["dpd.lambda_handler.handler"]
