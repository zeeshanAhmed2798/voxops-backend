import re

with open("app/main.py", "r", encoding="utf-8") as f:
    content = f.read()

new_desc = """    description=(
        "## Modules Implemented\\n"
        "- **Authentication**: Login, logout, current user, password change\\n"
        "- **User Profile**: View and update your profile\\n"
        "- **Departments**: Organization department directory\\n"
        "- **Jobs**: Field work, assignment, and status\\n"
    ),"""

content = re.sub(r'    description=\([\s\S]*?\),', new_desc, content)

content = re.sub(r'    contact=\{[\s\S]*?\},', '', content)
content = re.sub(r'    license_info=\{[\s\S]*?\},', '', content)

# cleanup double newlines and extra spaces if any, though it's fine.

with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(content)
