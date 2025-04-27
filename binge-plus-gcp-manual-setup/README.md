# Binge+ GCP Manual Setup

This script (`gcp_setup.py`) helps you set up the required Google Cloud Platform (GCP) infrastructure for Binge+.

## Prerequisites

Before running the script, ensure you have:

1. **A Google Cloud Project**
   - You must have a GCP project created and have the Project ID ready.

2. **Google Cloud SDK Installed & Authenticated**
   - Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) if you haven't already.
   - Authenticate using:
     ```sh
     gcloud auth application-default login
     ```

3. **Enable Required APIs**
   - You must manually enable the following APIs for your project:
     - **Identity and Access Management (IAM) API**
       - [Enable IAM API](https://console.developers.google.com/apis/api/iam.googleapis.com/overview?project=YOUR_PROJECT_ID)
     - **Cloud Resource Manager API**
       - [Enable Cloud Resource Manager API](https://console.developers.google.com/apis/api/cloudresourcemanager.googleapis.com/overview?project=YOUR_PROJECT_ID)
   - Replace `YOUR_PROJECT_ID` in the links above with your actual project ID.
   - After enabling, wait a few minutes for the changes to propagate.

4. **Python 3.7+**
   - Ensure you are using Python 3.7 or higher.

5. **Install Required Python Packages**
   - Install dependencies using:
     ```sh
     pip install -r requirements.txt
     ```

## How to Run the Script

1. Open a terminal and navigate to this directory:
   ```sh
   cd binge-plus-gcp-manual-setup
   ```
2. Run the setup script:
   ```sh
   python gcp_setup.py
   ```
3. When prompted, enter your GCP Project ID.

The script will:
- Authenticate your credentials
- Create a Terraform state bucket (if it doesn't exist)
- Create a service account and assign required roles
- Download the service account key as a JSON file

## Terraform State Bucket Naming

When creating the Terraform state bucket, the script will:

1. Try to create a bucket named `binge-plus-tfstate` (shared/global name).
2. If that name is unavailable (already taken globally), it will fall back to creating a bucket named `{your-project-id}-tfstate`.
3. If either bucket already exists, it will use the existing bucket and skip creation.

You will see messages in the terminal indicating which bucket name was used.

## Troubleshooting
- If you see errors about missing APIs, make sure you have enabled both the IAM API and Cloud Resource Manager API as described above.
- If you see missing module errors, ensure you have installed all dependencies from `requirements.txt`.

## Support
If you encounter issues, please check the error messages and ensure all prerequisites are met. If problems persist, contact the project maintainer. 