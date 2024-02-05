FROM python


WORKDIR /source



COPY requirements.txt .



RUN pip install --upgrade pip && pip install -r requirements.txt

VOLUME /source /download /packages

COPY ./src . 

CMD ["python3","checkUpdates.py"]
