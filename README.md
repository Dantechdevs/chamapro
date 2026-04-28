# ChamaPro 🤝

> **Professional group financial management for Kenyan chamas, SACCOs, and investment clubs.**

ChamaPro is a **Django-based platform** that digitizes and automates the full lifecycle of community savings groups — from member onboarding and contribution tracking to loan management, meeting coordination, and financial reporting. Built with the Kenyan chama ecosystem in mind.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.x-green?style=flat-square)](https://djangoproject.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Early%20Prototype-orange?style=flat-square)]()

---

## Screenshots

<img width="959" height="457" alt="ChamaPro Dashboard" src="https://github.com/user-attachments/assets/89249dde-c4eb-4c53-a7be-987cf7ce8b46" />
<img width="960" height="420" alt="ChamaPro Members View" src="https://github.com/user-attachments/assets/061984d2-605c-43f2-a3a8-819f98447270" />

---

## ✨ Features

### 👥 Member & Group Management
- Add, edit, and manage member profiles with full contact details
- Create and manage **multiple chamas** under a single account
- Role-based access: **Admin**, **Treasurer**, and **Member** roles
- Member invitation system and activity tracking

### 💰 Contributions & Finance
- Record, track, and reconcile member contributions
- Automated **penalty management** for late or missed payments — reflected on member statements
- Expense tracking (land purchases, services, operational costs)
- Bank account management — deposits, withdrawals, and transfers
- **Project/investment tracking** — monitor capital allocation across ventures (e.g. land, stocks, business)
- Downloadable financial statements — PDF and Excel export

### 🏦 Loan Management
- Apply for, approve, disburse, and track loan repayments
- Configurable loan terms and interest rates per chama
- Loan summaries and overdue tracking

### 📊 Reports & Analytics
- Member statements and contribution histories
- Cash flow statements, balance sheets, and P&L reports
- Loan summaries and expense breakdowns
- Group performance dashboard

### 📅 Meetings & Governance
- Schedule meetings with agendas
- Take attendance and log minutes
- Automated reminders for upcoming meetings

### 🔔 Notifications
- SMS and email alerts for contributions, loan repayments, and meetings
- Automated payment reminders to members

### 🔐 Security & Access
- Secure login with **Two-Factor Authentication (2FA)**
- Role-based permissions (Admin, Treasurer, Member)
- All data encrypted in transit and at rest

### 📱 Platform & Integrations
- Works on desktop, tablet, and mobile
- **REST API** — enables mobile apps and third-party integrations
- **M-Pesa integration** *(coming soon)* — STK push payments, wallet top-ups, and withdrawals to M-Pesa or bank account
- Cloud-hosted with 99.9% uptime target

---

## 🛠 Technology Stack

| Layer | Technology |
|---|---|
| Backend | Django (Python 3.10+) |
| Frontend | HTML, CSS, Bootstrap / Tailwind CSS |
| Database | PostgreSQL (production) / SQLite (dev) |
| Authentication | Django Auth + django-allauth + 2FA |
| API | Django REST Framework (DRF) |
| Payments | M-Pesa Daraja API *(planned)* |
| Notifications | Africa's Talking SMS API / SendGrid |
| Deployment | Docker + Nginx + Gunicorn |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- pip
- PostgreSQL (or SQLite for local dev)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/Dantechdevs/chamapro.git
cd chamapro
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example env file and update with your values:

```bash
cp .env.example .env
```

Key variables to set in `.env`:
```
SECRET_KEY=your-django-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:5432/chamapro
MPESA_CONSUMER_KEY=your-mpesa-key
MPESA_CONSUMER_SECRET=your-mpesa-secret
EMAIL_HOST_USER=your-email@gmail.com
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` in your browser.

---

## 📁 Project Structure

```
chamapro/
├── chama/                    # Core app — groups, members, contributions
├── loans/                    # Loan management module
├── meetings/                 # Meetings, agendas, minutes
├── reports/                  # Analytics and report generation
├── notifications/            # SMS and email alerts
├── api/                      # REST API (Django REST Framework)
├── templates/                # HTML templates
├── static/                   # CSS, JS, images
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🗺 Roadmap

| Phase | Module | Status |
|---|---|---|
| 1 | Project setup & authentication (2FA) | ✅ In progress |
| 2 | Member & group management | ✅ In progress |
| 3 | Contribution tracking & penalty management | 🔄 Planned |
| 4 | Loan management | 🔄 Planned |
| 5 | Expense, project & bank account management | 🔄 Planned |
| 6 | Meetings & governance module | 🔄 Planned |
| 7 | Reports & data export (PDF/Excel) | 🔄 Planned |
| 8 | REST API (DRF) | 🔄 Planned |
| 9 | SMS & email notifications | 🔄 Planned |
| 10 | M-Pesa Daraja integration | 🔄 Planned |
| 11 | Mobile app (React Native / Flutter) | 🔮 Future |

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Daniel Ngwasi (Dantechdevs)**
- Email: [damnngwasi@gmail.com](mailto:damnngwasi@gmail.com)
- GitHub: [@Dantechdevs](https://github.com/Dantechdevs)
- Location: Nairobi, Kenya 🇰🇪

---

> *ChamaPro — Built for Africa, by Africa.* 🌍
