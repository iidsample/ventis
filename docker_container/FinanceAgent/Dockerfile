FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV VENTIS_AGENT_NAME=FinanceAgent
ENV VENTIS_AGENT_FILE=finance_agent.py
ENV VENTIS_AGENT_PORT=50051

EXPOSE $VENTIS_AGENT_PORT

CMD python local_controller.py --port $VENTIS_AGENT_PORT
