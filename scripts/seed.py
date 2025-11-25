import requests
import argparse
import time
import random
import csv
from datetime import datetime
from faker import Faker

# Configuration
KEYCLOAK_URL = "http://localhost:7077"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
REALM_NAME = "superset"
CLIENT_ID = "dashboard"
CLIENT_SECRET = "rahasia123"

fake = Faker()


def get_admin_token():
    """Get admin access token from Keycloak"""
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    data = {
        "client_id": "admin-cli",
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD,
        "grant_type": "password"
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"[ERROR] Failed to get admin token: {e}")
        return None


def create_realm_if_not_exists():
    """Create realm 'superset' if it doesn't exist"""
    token = get_admin_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Check if realm exists
    check_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}"
    try:
        response = requests.get(check_url, headers=headers)
        if response.status_code == 200:
            print(f"[INFO] Realm '{REALM_NAME}' already exists")
            return True
    except:
        pass
    
    # Create realm
    create_url = f"{KEYCLOAK_URL}/admin/realms"
    realm_data = {
        "realm": REALM_NAME,
        "enabled": True,
        "displayName": "Superset Realm",
        "registrationAllowed": False,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False
    }
    
    try:
        response = requests.post(create_url, json=realm_data, headers=headers)
        response.raise_for_status()
        print(f"[SUCCESS] Realm '{REALM_NAME}' created successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create realm: {e}")
        return False


def create_client_if_not_exists():
    """Create client 'dashboard' for realm 'superset' if it doesn't exist"""
    token = get_admin_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get all clients
    clients_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients"
    try:
        response = requests.get(clients_url, headers=headers)
        response.raise_for_status()
        clients = response.json()
        
        # Check if client exists
        for client in clients:
            if client.get("clientId") == CLIENT_ID:
                print(f"[INFO] Client '{CLIENT_ID}' already exists")
                return True
    except Exception as e:
        print(f"[WARNING] Could not check existing clients: {e}")
    
    # Create client
    client_data = {
        "clientId": CLIENT_ID,
        "enabled": True,
        "publicClient": False,
        "secret": CLIENT_SECRET,
        "redirectUris": ["http://localhost:8088/*", "http://localhost:*"],
        "webOrigins": ["+"],
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": True,
        "authorizationServicesEnabled": False
    }
    
    try:
        response = requests.post(clients_url, json=client_data, headers=headers)
        response.raise_for_status()
        print(f"[SUCCESS] Client '{CLIENT_ID}' created successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create client: {e}")
        return False


def delete_existing_users_if_exists():
    """Delete all existing users in the realm"""
    token = get_admin_token()
    if not token:
        return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get all users
    users_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users"
    try:
        response = requests.get(users_url, headers=headers)
        response.raise_for_status()
        users = response.json()
        
        if not users:
            print("[INFO] No existing users to delete")
            return True
        
        print(f"[INFO] Found {len(users)} existing users, deleting...")
        deleted_count = 0
        
        for user in users:
            user_id = user.get("id")
            username = user.get("username")
            delete_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}"
            
            try:
                del_response = requests.delete(delete_url, headers=headers)
                del_response.raise_for_status()
                deleted_count += 1
                print(f"[DELETE] User deleted: {username}")
            except Exception as e:
                print(f"[ERROR] Failed to delete user {username}: {e}")
        
        print(f"[SUCCESS] Deleted {deleted_count}/{len(users)} users")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to delete existing users: {e}")
        return False


def seed_users_to_client(total_users, batch_size):
    """Seed users to the client with batch requests"""
    token = get_admin_token()
    if not token:
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    users_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users"
    
    # Prepare CSV file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"seeded_users_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Password', 'Status'])
        
        total_success = 0
        total_failed = 0
        
        # Process in batches
        for batch_num in range(0, total_users, batch_size):
            batch_end = min(batch_num + batch_size, total_users)
            current_batch_size = batch_end - batch_num
            
            print(f"\n[BATCH] Processing batch {batch_num//batch_size + 1} (users {batch_num + 1}-{batch_end})...")
            
            batch_success = 0
            batch_failed = 0
            
            for i in range(current_batch_size):
                user_num = batch_num + i + 1
                
                # Generate user data with format '01'-'20' and password Pusilkom123
                first_name = fake.first_name()
                last_name = fake.last_name()
                username = f"user{user_num:02d}"  # Changed to user01, user02, etc.
                email = f"{username}@example.com"
                password = "Pusilkom123"
                
                user_data = {
                    "username": username,
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "enabled": True,
                    "emailVerified": True,
                    "credentials": [{
                        "type": "password",
                        "value": password,
                        "temporary": False
                    }]
                }
                
                try:
                    response = requests.post(users_url, json=user_data, headers=headers)
                    response.raise_for_status()
                    
                    # Success
                    batch_success += 1
                    total_success += 1
                    status = "SUCCESS"
                    print(f"[{user_num}/{total_users}] Created: {username} ({email})")
                    
                    # Write to CSV
                    csv_writer.writerow([username, email, first_name, last_name, password, status])
                    csvfile.flush()
                    
                except Exception as e:
                    # Failed - show detailed error
                    batch_failed += 1
                    total_failed += 1
                    error_detail = str(e)
                    
                    # Try to get detailed error message from response
                    try:
                        if hasattr(e, 'response') and e.response is not None:
                            error_json = e.response.json()
                            error_detail = error_json.get('errorMessage', error_json.get('error', str(e)))
                    except:
                        pass
                    
                    status = f"FAILED: {error_detail}"
                    print(f"[{user_num}/{total_users}] Failed: {username}")
                    print(f"  Error: {error_detail}")
                    
                    # Debug: print the user data being sent
                    if batch_failed == 1:  # Only print once per batch
                        print(f"  Debug - User data sent: {user_data}")
            
            print(f"[SUMMARY] Batch: {batch_success} success, {batch_failed} failed")
            
            # Random delay between batches (except for the last batch)
            if batch_end < total_users:
                delay = random.randint(5, 10)
                print(f"[WAIT] Waiting {delay} seconds before next batch...")
                time.sleep(delay)
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"SEEDING COMPLETED")
        print(f"{'='*60}")
        print(f"Total users processed: {total_users}")
        print(f"Successfully created: {total_success}")
        print(f"Failed: {total_failed}")
        print(f"CSV file saved: {csv_filename}")
        print(f"{'='*60}")


# Entrypoint
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Seed users to Keycloak')
    parser.add_argument('--total-users', type=int, default=20, help='Total number of users to create')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of users per batch')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"KEYCLOAK USER SEEDING SCRIPT")
    print(f"{'='*60}")
    print(f"Keycloak URL: {KEYCLOAK_URL}")
    print(f"Realm: {REALM_NAME}")
    print(f"Client: {CLIENT_ID}")
    print(f"Total users: {args.total_users}")
    print(f"Batch size: {args.batch_size}")
    print(f"{'='*60}\n")
    
    create_realm_if_not_exists()
    create_client_if_not_exists()
    delete_existing_users_if_exists()
    seed_users_to_client(args.total_users, args.batch_size)

# Example usage:
# python scripts/seed.py --total-users 10 --batch-size 5
# python scripts/seed.py --total-users 100 --batch-size 20