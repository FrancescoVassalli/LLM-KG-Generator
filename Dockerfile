# Use an official Python runtime as a parent image
FROM python:3.11.4-bookworm

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD ./pyproject.toml /app/pyproject.toml
ADD ./README.md /app/README.md

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir poetry \
    && poetry install --no-root --without dev

ADD . /app
# Make port 8000 available to the world outside this container
EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]