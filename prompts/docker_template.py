docker_template = """
# Use an appropriate base image
# For Python projects, use a Python base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone the repository (if applicable)
RUN git clone https://github.com/your-username/your-repo.git .

# Install project dependencies (if using pip)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set up the environment (if using Conda)
# Uncomment the following lines if you need to create a Conda environment
# RUN conda create -n myenv python=3.12 -y
# RUN echo "conda activate myenv" >> ~/.bashrc
# ENV PATH /opt/conda/envs/myenv/bin:$PATH

# Install additional dependencies (if using Conda)
# Uncomment the following lines if you need to install Conda dependencies
# COPY environment.yml .
# RUN conda env update -n myenv -f environment.yml

# Expose any necessary ports
EXPOSE 8000

# Set the default command to run the application
CMD ["python", "your_main_script.py"]
"""
