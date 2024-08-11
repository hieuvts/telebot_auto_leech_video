FROM python:3.11.2

COPY .env main.py ./

RUN pip install -U python-dotenv

RUN pip install yt-dlp
RUN pip install python-telegram-bot

CMD ["python3", "./main.py"]
