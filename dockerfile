# # Use the official AWS Lambda Python 3.11 runtime image
# FROM public.ecr.aws/lambda/python:3.11

# # Install system libraries for psycopg2 and SSH
# RUN yum update -y && \
#     yum install -y gcc gcc-c++ make postgresql-devel openssh-clients

# # Install required Python libraries
# RUN python3.11 -m pip install psycopg2-binary sshtunnel pymysql boto3

# # Copy the Lambda function
# COPY lambda_function.py .

# # Copy the private key & set correct permissions
# # COPY ohio.pem /root/.ssh/id_rsa
# # RUN chmod 400 /root/.ssh/id_rsa && chown root:root /root/.ssh/id_rsa

# # COPY ohio.pem /tmp/id_rsa
# # RUN chmod 400 /tmp/id_rsa


# # Run the container as root
# USER root

# # Set the Lambda entry point
# CMD ["lambda_function.lambda_handler"]

#CODE FROM BOLT

# Use the official AWS Lambda Python 3.11 runtime image
FROM public.ecr.aws/lambda/python:3.11

# Install system libraries for psycopg2 and SSH
RUN yum update -y && \
    yum install -y gcc gcc-c++ make postgresql-devel openssh-clients && \
    yum clean all && \
    rm -rf /var/cache/yum

# Install required Python libraries
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.9 \
    sshtunnel==0.4.0 \
    paramiko==3.4.0 \
    pymysql==1.1.0 \
    boto3==1.34.34

# Create necessary directories
RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh

# Copy the Lambda function
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set proper permissions for the Lambda task root
RUN chmod 755 ${LAMBDA_TASK_ROOT}

# Run the container as root (required for SSH operations)
USER root

# Set the Lambda handler
CMD ["lambda_function.lambda_handler"]
