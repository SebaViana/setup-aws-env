import boto3
import sys
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

def validate_arguments():
    if len(sys.argv) != 4:
        print("Usage: python terraform-baseline-setup.py <bucket_name> <table_name> <region>")
        sys.exit(1)  # Exit with an error code

def validate_aws_credentials(region):
    try:
        # Create an S3 client
        test_s3_client = boto3.client('s3', region_name=region)

        # Attempt to list S3 buckets
        test_s3_client.list_buckets()
        print("AWS credentials are valid.")

    except NoCredentialsError:
        print("Error: AWS credentials not found. Please configure your AWS credentials.")
        sys.exit(1)  # Exit with an error code

    except PartialCredentialsError:
        print("Error: Incomplete AWS credentials. Please check your AWS credentials configuration.")
        sys.exit(1)  # Exit with an error code

    except ClientError as e:
        # This handles other client errors, such as insufficient permissions
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            print("Error: Access denied. Please check your AWS IAM permissions.")
        else:
            print(f"Error: {e}")
        sys.exit(1)  # Exit with an error code

    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)  # Exit with an error code

def check_dynamodb_table_exists(table_name, region):
    dynamodb_client = boto3.client('dynamodb', region_name=region)
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except dynamodb_client.exceptions.ResourceNotFoundException:
        return False
    except ClientError as e:
        print(f"Error checking DynamoDB table: {e}")
        sys.exit(1)  # Exit with an error code

def create_s3_bucket(bucket_name, region):
    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': region
            }
        )
        # Enable versioning
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        # Enable server-side encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [{
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256'
                    }
                }]
            }
        )
        print(f"S3 bucket '{bucket_name}' created and configured.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyExists':
            print(f"Error creating S3 bucket: The requested bucket name '{bucket_name}' is already in use. Please choose a different name.")
        else:
            print(f"Error creating S3 bucket: {e}")
        sys.exit(1)  # Exit with an error code

def create_dynamodb_table(table_name, region):
    try:
        dynamodb_client = boto3.client('dynamodb', region_name=region)
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'LockID',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'LockID',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"DynamoDB table '{table_name}' created.")
    except ClientError as e:
        print(f"Error creating DynamoDB table: {e}")

if __name__ == "__main__":
    validate_arguments()

    # Get arguments passed from the workflow
    bucket_name = sys.argv[1]
    table_name = sys.argv[2]
    region = sys.argv[3]

    validate_aws_credentials(region)

    # Check if the DynamoDB table already exists
    dynamodb_exists = check_dynamodb_table_exists(table_name, region)


    if dynamodb_exists:
        print(f"DynamoDB table '{table_name}' already exists.")
        print("Aborting DynamoDB creation process as the table already exists.")
    else:
        # Proceed with creating the DynamoDB table and S3 bucket if neither exist
        create_s3_bucket(bucket_name, region)
        create_dynamodb_table(table_name, region)
