import os
import json
import paramiko
import sshtunnel
import psycopg2
import logging
import base64

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Database configuration
BASTION_HOST = '18.117.139.7'
BASTION_USER = 'ubuntu'
RDS_HOST = 'lambdards.cfe2kb03konk.us-east-2.rds.amazonaws.com'
RDS_USER = 'lambdards'
RDS_PASSWORD = 'OyVcei45PR9cV$wINlS1l~awGfZg'
RDS_DB = 'lambdards'
PORT = 5432
SSH_KEY_PATH = '/tmp/id_rsa'

def format_ssh_key(key_content):
    """Ensure SSH key is properly formatted with correct line endings"""
    # Remove any existing line endings and spaces
    key_content = key_content.strip()
    
    # Check if the key is base64 encoded
    try:
        if not key_content.startswith('-----'):
            # Try to decode if it's base64 encoded
            key_content = base64.b64decode(key_content).decode('utf-8')
    except:
        pass

    # Ensure key has proper format
    if not key_content.startswith('-----BEGIN'):
        raise ValueError("SSH key must start with '-----BEGIN'")
    
    # Ensure proper line endings
    key_parts = key_content.split('-----')
    if len(key_parts) >= 4:
        begin_part = f"-----{key_parts[1]}-----\n"
        key_body = key_parts[2].strip()
        end_part = f"\n-----{key_parts[3]}-----\n"
        
        # Format key body with proper line lengths
        key_body_lines = [key_body[i:i+64] for i in range(0, len(key_body), 64)]
        formatted_key_body = '\n'.join(key_body_lines)
        
        return f"{begin_part}{formatted_key_body}{end_part}"
    
    raise ValueError("Invalid SSH key format")

def setup_ssh_key(ssh_key_content):
    """Setup SSH key with proper formatting and permissions"""
    try:
        # Format the SSH key
        formatted_key = format_ssh_key(ssh_key_content)
        
        # Write the formatted key to file
        with open(SSH_KEY_PATH, 'w') as key_file:
            key_file.write(formatted_key)
        
        # Set correct permissions
        os.chmod(SSH_KEY_PATH, 0o400)
        
        # Verify the key can be loaded
        try:
            paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
        except Exception as e:
            raise ValueError(f"Invalid key after formatting: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error setting up SSH key: {str(e)}")
        raise

def create_db_connection(tunnel):
    """Create database connection through SSH tunnel"""
    return psycopg2.connect(
        host='127.0.0.1',
        port=tunnel.local_bind_port,
        database=RDS_DB,
        user=RDS_USER,
        password=RDS_PASSWORD
    )

def lambda_handler(event, context):
    """Main Lambda handler function"""
    try:
        # Get SSH key from environment variable
        ssh_key_content = os.getenv('SSH_PRIVATE_KEY')
        if not ssh_key_content:
            raise ValueError("SSH_PRIVATE_KEY environment variable is missing")

        logger.info("Received SSH key content")
        
        # Setup SSH key
        setup_ssh_key(ssh_key_content)
        logger.info("SSH key setup completed")

        # Create SSH key object
        private_key = paramiko.RSAKey.from_private_key_file(SSH_KEY_PATH)
        logger.info("SSH key loaded successfully")

        # Establish SSH tunnel
        with sshtunnel.open_tunnel(
            (BASTION_HOST, 22),
            ssh_username=BASTION_USER,
            ssh_pkey=private_key,
            remote_bind_address=(RDS_HOST, PORT),
            local_bind_address=('0.0.0.0', 0)
        ) as tunnel:
            logger.info("SSH Tunnel established successfully")

            # Create database connection
            with create_db_connection(tunnel) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    db_version = cursor.fetchone()
                    logger.info(f"Database version: {db_version}")

                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Database connection successful',
                            'dbVersion': str(db_version)
                        })
                    }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Error connecting to database'
            })
        }
    finally:
        # Cleanup
        if os.path.exists(SSH_KEY_PATH):
            os.remove(SSH_KEY_PATH)

