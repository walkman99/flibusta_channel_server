FROM python:3.9.1

RUN pip install --no-cache-dir pip

COPY requirements.txt /usr/src/app/

RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt

COPY ./source/db.py /usr/src/app/db.py
COPY ./source/main.py /usr/src/app/main.py
COPY ./source/config.py /usr/src/app/config.py

CMD cd /usr/src/app/ && python main.py
