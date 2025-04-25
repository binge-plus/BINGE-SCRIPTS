import os
import sys
import re
import json

# Ensure google-cloud libraries are installed
try:
    from google.cloud import storage
    from google.cloud import iam
    from google.cloud import resourcemanager_v3
    import google.auth
    from google.auth import exceptions as auth_exceptions
except ImportError as e:
    print(f"❌ Missing required libraries: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

class GCPSetup:
    def __init__(self, project_id=None):
        # Predefined region and zone
        self.region = "us-central1"
        self.zone = "us-central1-a"
        self.service_account_name = "binge-plus-sa"
        
        # Roles to assign
        self.roles = [
            "roles/artifactregistry.admin",
            "roles/bigquery.dataViewer",
            "roles/run.viewer",
            "roles/cloudsql.viewer",
            "roles/compute.admin",
            "roles/compute.networkAdmin",
            "roles/compute.storageAdmin",
            "roles/compute.viewer",
            "roles/resourcemanager.projectIamAdmin",
            "roles/pubsub.viewer",
            "roles/iam.serviceAccountAdmin",
            "roles/iam.serviceAccountKeyAdmin",
            "roles/storage.objectAdmin"
        ]
        
        # Project ID
        self.project_id = project_id

    def validate_project_id(self, project_id):
        """Validate the project ID format."""
        pattern = r'^[a-z0-9-]{6,30}$'
        if not re.match(pattern, project_id):
            raise ValueError("Invalid Project ID. Must be 6-30 characters long, using lowercase letters, numbers, and hyphens.")
        return project_id

    def authenticate(self):
        """Authenticate with Google Cloud."""
        try:
            # Attempt to get default credentials
            credentials, project = google.auth.default()
            print("✅ Authentication successful!")
            return credentials
        except auth_exceptions.DefaultCredentialsError:
            print("❌ Authentication failed. Please run 'gcloud auth application-default login'")
            sys.exit(1)

    def create_tfstate_bucket(self, credentials):
        """Create a Terraform state bucket."""
        try:
            # Initialize storage client
            storage_client = storage.Client(
                credentials=credentials, 
                project=self.project_id
            )
            
            # Bucket name
            bucket_name = f"{self.project_id}-tfstate"
            
            # Check if bucket exists
            bucket = storage_client.bucket(bucket_name)
            if bucket.exists():
                print(f"⚠️ Bucket {bucket_name} already exists. Skipping creation.")
                return
            
            # Create bucket
            bucket = storage_client.create_bucket(bucket_name)
            
            # Enable versioning
            bucket.versioning_enabled = True
            bucket.patch()
            
            print(f"✅ Terraform state bucket {bucket_name} created successfully!")
        
        except Exception as e:
            print(f"❌ Error creating bucket: {e}")
            sys.exit(1)

    def create_service_account(self, credentials):
        """Create service account and assign roles."""
        try:
            # IAM client
            iam_client = iam.IAMClient(credentials=credentials)
            
            # Resource manager client
            project_client = resourcemanager_v3.ProjectsClient(credentials=credentials)
            
            # Full service account name
            service_account_email = f"{self.service_account_name}@{self.project_id}.iam.gserviceaccount.com"
            
            # Check if service account exists
            try:
                iam_client.get_service_account(
                    name=f"projects/{self.project_id}/serviceAccounts/{service_account_email}"
                )
                print(f"⚠️ Service account {service_account_email} already exists.")
            except Exception:
                # Create service account
                service_account = iam_client.create_service_account(
                    request={
                        "account_id": self.service_account_name,
                        "service_account": {
                            "display_name": "Binge Plus Service Account",
                            "description": "Service Account for Binge Plus application"
                        },
                        "project_id": self.project_id
                    }
                )
                print(f"✅ Service account {service_account_email} created successfully!")
            
            # Assign roles
            for role in self.roles:
                try:
                    # Create policy binding
                    policy = project_client.get_iam_policy(request={"project": self.project_id})
                    
                    # Add binding
                    binding = {
                        "role": role,
                        "members": [f"serviceAccount:{service_account_email}"]
                    }
                    policy.bindings.append(binding)
                    
                    # Set updated policy
                    project_client.set_iam_policy(
                        request={
                            "project": self.project_id,
                            "policy": policy
                        }
                    )
                    print(f"✅ Assigned role: {role}")
                except Exception as role_error:
                    print(f"❌ Error assigning role {role}: {role_error}")
            
            # Create service account key
            key_path = f"{self.service_account_name}-key.json"
            key = iam_client.create_service_account_key(
                request={
                    "name": f"projects/{self.project_id}/serviceAccounts/{service_account_email}",
                    "private_key_type": iam.ServiceAccountPrivateKeyType.TYPE_GOOGLE_CREDENTIALS_JSON
                }
            )
            
            # Save key to file
            with open(key_path, 'wb') as f:
                f.write(key.private_key_data)
            
            print(f"✅ Service account key saved to {key_path}")
        
        except Exception as e:
            print(f"❌ Error creating service account: {e}")
            sys.exit(1)

    def run(self):
        """Main execution method."""
        # Get project ID if not provided
        if not self.project_id:
            while True:
                try:
                    self.project_id = input("Enter your GCP Project ID: ")
                    self.project_id = self.validate_project_id(self.project_id)
                    break
                except ValueError as e:
                    print(f"❌ {e}")

        print("🚀 Binge+ GCP Infrastructure Setup")
        print("--------------------------------")

        # Authenticate
        credentials = self.authenticate()

        # Create Terraform state bucket
        self.create_tfstate_bucket(credentials)

        # Create service account
        self.create_service_account(credentials)

        print("✅ GCP infrastructure setup completed successfully!")

def main():
    setup = GCPSetup()
    setup.run()

if __name__ == "__main__":
    main() 