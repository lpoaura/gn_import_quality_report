FROM dhi.io/python:3.13

RUN useradd -ms /bin /bash user
USER user

WORKDIR /home/user

COPY requirements.txt .
RUN pip install -r requirements.txt && rm requirements.txt

COPY src .

ENTRYPOINT ["python", "main.py"]