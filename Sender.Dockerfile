FROM python:3.8.2
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt
COPY ./source/config.py /usr/src/app/config.py
COPY ./source/sender.py /usr/src/app/sender.py
CMD cd /usr/src/app/ && python sender.py
