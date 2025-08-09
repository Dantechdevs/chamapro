# ChamaPro

ChamaPro is a **Django-based group financial management system** designed to help community savings groups, investment clubs, and chamas manage their contributions, loans, expenses, and meetings with ease.

## Features (Planned)
- Member registration and management  
- Contribution tracking (monthly/weekly/daily)  
- Loan management with interest calculation  
- Expense and income tracking  
- Reports and analytics (PDF & Excel export)  
- Role-based user access control  
- Notifications (Email, SMS, WhatsApp integration)  
- Mobile-friendly responsive design  

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
