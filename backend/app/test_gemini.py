from app.services.gemini_services import generate_project

response = generate_project(
    project_name="Library Management System",
    project_type='Website',
    requirements="""
    Build a Library Management System with:
    - JWT Authentication
    - Book Management
    - Borrow & Return Books
    - Reporting Dashboard
    - Email Notifications
    """
)

print(response.model_dump_json(indent=4))