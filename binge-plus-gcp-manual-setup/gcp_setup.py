import os
import sys
import re
import json

# Ensure google-cloud libraries are installed
try:
    from google.cloud import storage
    from google.cloud import resourcemanager_v3
    import google.auth
    from google.auth import exceptions as auth_exceptions
    from googleapiclient import discovery
    from googleapiclient.errors import HttpError
    from google.api_core.exceptions import Forbidden
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
            storage_client = storage.Client(
                credentials=credentials, 
                project=self.project_id
            )

            preferred_bucket_name = "binge-plus-tfstate"
            fallback_bucket_name = f"{self.project_id}-tfstate"

            # Try preferred bucket name first
            try:
                bucket = storage_client.bucket(preferred_bucket_name)
                if bucket.exists():
                    print(f"⚠️ Bucket {preferred_bucket_name} already exists. Skipping creation.")
                    print(f"Using existing bucket: {preferred_bucket_name}")
                    return
                try:
                    bucket = storage_client.create_bucket(preferred_bucket_name)
                    bucket.versioning_enabled = True
                    bucket.patch()
                    print(f"✅ Terraform state bucket {preferred_bucket_name} created successfully!")
                    return
                except Exception as e:
                    print(f"⚠️ Could not create bucket '{preferred_bucket_name}': {e}")
                    print(f"Attempting to create fallback bucket: {fallback_bucket_name}")
            except Forbidden as e:
                print(f"⚠️ Permission denied for bucket '{preferred_bucket_name}': {e}")
                print(f"Attempting to create fallback bucket: {fallback_bucket_name}")
            except Exception as e:
                # If any other error occurs, also try fallback
                print(f"⚠️ Error checking bucket '{preferred_bucket_name}': {e}")
                print(f"Attempting to create fallback bucket: {fallback_bucket_name}")

            # Fallback to project-specific bucket name
            bucket = storage_client.bucket(fallback_bucket_name)
            if bucket.exists():
                print(f"⚠️ Bucket {fallback_bucket_name} already exists. Skipping creation.")
                print(f"Using existing bucket: {fallback_bucket_name}")
                return
            bucket = storage_client.create_bucket(fallback_bucket_name)
            bucket.versioning_enabled = True
            bucket.patch()
            print(f"✅ Terraform state bucket {fallback_bucket_name} created successfully!")

        except Exception as e:
            print(f"❌ Error creating bucket: {e}")
            sys.exit(1)

    def create_service_account(self, credentials):
        """Create service account and assign roles."""
        try:
            import base64
            from google.oauth2 import service_account

            service = discovery.build('iam', 'v1', credentials=credentials)
            crm_service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)

            service_account_email = f"{self.service_account_name}@{self.project_id}.iam.gserviceaccount.com"
            service_account_id = self.service_account_name
            project_path = f"projects/{self.project_id}"
            sa_path = f"projects/{self.project_id}/serviceAccounts/{service_account_email}"

            # Check if service account exists
            try:
                service.projects().serviceAccounts().get(name=sa_path).execute()
                print(f"⚠️ Service account {service_account_email} already exists.")
            except HttpError as e:
                if e.resp.status == 404:
                    # Create service account
                    sa_body = {
                        "accountId": service_account_id,
                        "serviceAccount": {
                            "displayName": "Binge Plus Service Account",
                            "description": "Service Account for Binge Plus application"
                        }
                    }
                    service.projects().serviceAccounts().create(name=project_path, body=sa_body).execute()
                    print(f"✅ Service account {service_account_email} created successfully!")
                else:
                    raise

            # Assign roles
            policy = crm_service.projects().getIamPolicy(resource=self.project_id, body={}).execute()
            bindings = policy.get('bindings', [])
            member = f"serviceAccount:{service_account_email}"
            for role in self.roles:
                role_binding = next((b for b in bindings if b['role'] == role), None)
                if role_binding:
                    if member in role_binding['members']:
                        print(f"⚠️ Role {role} already assigned.")
                        continue
                    else:
                        role_binding['members'].append(member)
                else:
                    bindings.append({
                        'role': role,
                        'members': [member]
                    })
                print(f"✅ Assigned role: {role}")
            policy['bindings'] = bindings
            crm_service.projects().setIamPolicy(resource=self.project_id, body={'policy': policy}).execute()

            # Create service account key
            key_path = f"{self.service_account_name}-key.json"
            key = service.projects().serviceAccounts().keys().create(
                name=sa_path,
                body={
                    "privateKeyType": "TYPE_GOOGLE_CREDENTIALS_FILE",
                    "keyAlgorithm": "KEY_ALG_RSA_2048"
                }
            ).execute()
            private_key_data = base64.b64decode(key['privateKeyData'])
            with open(key_path, 'wb') as f:
                f.write(private_key_data)
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