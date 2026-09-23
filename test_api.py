import requests
import time
import uuid
import sys

BASE_URL = "http://127.0.0.1:8000"
session = requests.Session()

def print_result(name, res):
    if res.status_code in [200, 201, 204]:
        print(f"✅ {name} (Status: {res.status_code})")
    else:
        print(f"❌ {name} (Status: {res.status_code})")
        print(f"   Response: {res.text}")
        sys.exit(1)

def main():
    print("🚀 Starting API Tests...\n")
    
    unique_id = uuid.uuid4().hex[:6]
    admin_email = f"admin_{unique_id}@acme.com"
    member_email = f"member_{unique_id}@acme.com"
    
    # 1. Health Checks
    print_result("Health Check", session.get(f"{BASE_URL}/health"))
    print_result("Root Check", session.get(f"{BASE_URL}/"))
    
    # 2. Auth - Register Admin
    print("\n--- 🔐 Auth & Registration ---")
    res = session.post(f"{BASE_URL}/api/v1/auth/register", json={
        "org_name": f"Acme Corp {unique_id}",
        "full_name": "Admin User",
        "email": admin_email,
        "password": "SecurePassword123!"
    })
    print_result("Register Org + Admin", res)
    tokens = res.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 3. Auth - Resend Verification
    res = session.post(f"{BASE_URL}/api/v1/auth/resend-verification-email", json={
        "email": admin_email
    })
    print_result("Resend Verification Email", res)
    
    # 4. Auth - Invite Member
    res = session.post(f"{BASE_URL}/api/v1/auth/invite-member", headers=headers, json={
        "email": member_email,
        "full_name": "New Member",
        "role": "EMPLOYEE"
    })
    print_result("Invite Member", res)
    
    # In APP_ENV=development, the invite_token is returned in the response
    invite_token = res.json().get("invite_token")
    if not invite_token:
        print("⚠️ Could not extract invite token (APP_ENV might not be development)")
    else:
        # 5. Auth - Register Member
        res = session.post(f"{BASE_URL}/api/v1/auth/register-member", json={
            "invite_token": invite_token,
            "full_name": "New Member",
            "password": "MemberPassword123!"
        })
        print_result("Register Member (via Invite)", res)
    
    # 6. Auth - Login
    print("\n--- 🔑 Login & Session ---")
    res = session.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": admin_email,
        "password": "SecurePassword123!"
    })
    print_result("Login", res)
    access_token = res.json()["access_token"]
    refresh_token = res.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 7. Auth - Refresh
    res = session.post(f"{BASE_URL}/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    print_result("Refresh Token", res)
    access_token = res.json()["access_token"]
    refresh_token = res.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 8. Auth - Get Current User
    res = session.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    print_result("Get Current User (/auth/me)", res)
    
    # 9. Profile - Get / Update
    print("\n--- 👤 User Profile ---")
    res = session.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
    print_result("Get My Profile", res)
    
    res = session.patch(f"{BASE_URL}/api/v1/users/me", headers=headers, json={
        "job_title": "CEO",
        "phone": "+1-555-0123"
    })
    print_result("Update My Profile", res)
    
    # 10. Knowledge Base
    print("\n--- 📚 Knowledge Base ---")
    res = session.post(f"{BASE_URL}/api/v1/knowledge-base", headers=headers, json={
        "title": "Welcome to Acme",
        "content": "This is a test document.",
        "category": "General",
        "is_published": True
    })
    print_result("Create Document", res)
    doc_id = res.json()["id"]
    
    res = session.get(f"{BASE_URL}/api/v1/knowledge-base", headers=headers)
    print_result("List Documents", res)
    
    res = session.get(f"{BASE_URL}/api/v1/knowledge-base/{doc_id}", headers=headers)
    print_result("Get Document", res)
    
    res = session.put(f"{BASE_URL}/api/v1/knowledge-base/{doc_id}", headers=headers, json={
        "title": "Welcome to Acme (Updated)"
    })
    print_result("Update Document", res)
    
    res = session.delete(f"{BASE_URL}/api/v1/knowledge-base/{doc_id}", headers=headers)
    print_result("Delete Document", res)
    
    # 11. Auth - Change Password
    print("\n--- 🔒 Auth Password Management ---")
    res = session.post(f"{BASE_URL}/api/v1/auth/change-password", headers=headers, json={
        "current_password": "SecurePassword123!",
        "new_password": "NewSecurePassword123!"
    })
    print_result("Change Password", res)
    
    # 12. Auth - Forgot Password
    res = session.post(f"{BASE_URL}/api/v1/auth/forgot-password", json={
        "email": admin_email
    })
    print_result("Forgot Password", res)
    reset_token = res.json().get("reset_token")
    
    if reset_token:
        # 13. Auth - Reset Password
        res = session.post(f"{BASE_URL}/api/v1/auth/reset-password", json={
            "token": reset_token,
            "new_password": "ResetPassword123!"
        })
        print_result("Reset Password", res)
    else:
        print("⚠️ Could not extract reset token (APP_ENV might not be development)")
        
    # 14. Auth - Logout
    res = session.post(f"{BASE_URL}/api/v1/auth/logout", headers=headers, json={
        "refresh_token": refresh_token
    })
    print_result("Logout", res)
    
    print("\n🎉 All tests passed successfully!")

if __name__ == "__main__":
    # give server 2 seconds to be fully ready
    time.sleep(2)
    main()
