# ChamaPro

ChamaPro is a **Django-based group financial management system** designed to help community savings groups, investment clubs, and chamas manage their contributions, loans, expenses, and meetings with ease.

## 🚀 Features

- **Member Management** – Add, edit, and manage member profiles with contact details.
- **Chama Groups** – Create and manage multiple chamas under one account.
- **Contributions Tracking** – Record, track, and report member contributions.
- **Loan Management** – Approve, disburse, and track loan repayments.
- **Meetings & Agendas** – Schedule meetings, take attendance, and log minutes.
- **Reports & Analytics** – View group performance, contributions, and loans.
- **Role-Based Access Control** – Admins, Treasurers, and Members.
- **Secure Authentication** – Login, password reset, and 2FA ready.
- **Multi-Device Support** – Works on desktop, tablet, and mobile.
- **API Ready** – REST API for mobile and third-party integrations.

## Technology Stack
- **Backend:** Django (Python)  
- **Frontend:** HTML, CSS, Bootstrap (or Tailwind)  
- **Database:** PostgreSQL or MySQL  
- **Authentication:** Django's built-in auth with role-based permissions  

## Installation (Development)

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/ChamaPro.git
cd ChamaPro
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate    # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure database settings
Edit your `settings.py` file and update the database connection details.

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Start the development server
```bash
python manage.py runserver
```

## Project Structure (Planned)
```
ChamaPro/
├── chama/                # Main Django app
├── templates/            # HTML templates
├── static/               # CSS, JS, images
├── manage.py
└── README.md
```

## Roadmap
- Step 1: Project setup with Django  
- Step 2: Member management module  
- Step 3: Contribution tracking module  
- Step 4: Loan management module  
- Step 5: Expense and income tracking  
- Step 6: Reports & exports  
- Step 7: Notifications integration  

## License
This project is licensed under the MIT License.

**Author:** Dantechdevs  
**Email:** damnngwasi@gmail.com  
**GitHub:** [https://github.com/Dantechdevs](https://github.com/Dantechdevs)
