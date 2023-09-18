FROM python:3.9-bullseye

# Installing/Updating system dependencies
RUN apt update -y
RUN apt install postgresql git curl -y

# Install rust toolchain
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Update pip
RUN pip install --upgrade pip

WORKDIR /bot

# Install python dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy source code
COPY . .

CMD ["python3", "main.py"]