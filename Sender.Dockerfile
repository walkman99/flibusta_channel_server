FROM python:3.9.5

RUN pip install --no-cache-dir -U pip wheel

COPY requirements.txt /usr/src/app/

RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt

COPY ./source/config.py /usr/src/app/config.py
COPY ./source/db.py /usr/src/app/db.py
COPY ./source/sender.py /usr/src/app/sender.py

CMD cd /usr/src/app/ && python sender.py
