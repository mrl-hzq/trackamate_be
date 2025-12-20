# TracKaMate Backend

> Personal finance and nutrition tracking API built with Flask

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.1-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

TracKaMate is a comprehensive personal finance and nutrition tracking backend application. It helps users manage income, allocate funds across spending categories, track meals with AI-powered nutrition detection, and maintain financial discipline through a unique salary cycle system (25th-24th of each month).

### Key Features

- **Income Management** - Track income with automatic allocation to spending pools (20% burn, 30% invest, 50% commit)
- **Smart Spending Pools**
  - **Burn** - Discretionary spending (fun money)
  - **Invest** - Investment tracking with risk categories
  - **Commit** - Committed expenses (bills, groceries, rent)
- **Food Tracking** - AI-powered nutrition detection using OpenAI Vision API
- **Goals & Reminders** - Set financial and health goals with automated reminders
- **Image Upload** - Receipt and proof photo support across all transaction types
- **JWT Authentication** - Secure user authentication and authorization
- **Salary Cycle Based** - Custom pay cycle tracking (25th to 24th)

## Quick Start

### Prerequisites

- Python 3.13+
- MySQL 8.0+
- OpenAI API Key (for food tracking)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd trackamate_be
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-key-here
   DATABASE_URI=mysql+pymysql://username:password@localhost/trackamate_db
   OPENAI_API_KEY=sk-proj-your-openai-key-here
   ```

5. **Initialize database**
   ```bash
   python setup_db.py
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

Server runs on `http://localhost:5000`

## API Endpoints

### Authentication
- `POST /user/register` - Register new user
- `POST /user/login` - Login and get JWT token
- `GET /user/me` - Get current user profile (protected)

### Income
- `POST /income/add_income` - Add income with automatic pool allocation
- `GET /income/get_pools/:user_id` - Get pool balances for current cycle

### Burn (Discretionary Spending)
- `POST /burn/add_burn` - Add discretionary spending
- `GET /burn/total_burn/:user_id` - Get all burns for current cycle
- `PUT /burn/update_burn/:id` - Update burn record
- `DELETE /burn/delete_burn/:id` - Delete burn record

### Invest
- `POST /invest/add_invest` - Add investment
- `GET /invest/total_invest/:user_id` - Get all investments for current cycle
- `PUT /invest/edit_invest/:invest_id` - Update investment
- `DELETE /invest/delete_invest/:invest_id` - Delete investment

### Commit (Fixed Expenses)
- `POST /commit/add_commit` - Add committed expense
- `GET /commit/total_commit/:user_id` - Get all commits for current cycle
- `PUT /commit/edit_commit/:commit_id` - Update commitment
- `DELETE /commit/delete_commit/:commit_id` - Delete commitment

### Food Tracking
- `POST /food/analyze_food` - AI-powered nutrition detection from photo
- `POST /food/add_food` - Add meal entry
- `GET /food/get_food/:user_id` - Get all meals
- `PUT /food/edit_food/:meal_id` - Update meal
- `GET /food/view_food_setting/:user_id` - Get food settings

### Image Access
- `GET /uploads/:folder/:filename` - Access uploaded images

See [API Documentation](docs/api/) for detailed endpoint information.

## Documentation

- **[Getting Started Guide](DEVELOPMENT.md)** - Complete setup and development guide
- **[API Reference](docs/api/)** - Detailed API endpoint documentation
- **[Database Schema](docs/reference/database-schema.md)** - Database models and relationships
- **[Image Uploads Guide](docs/api/image-uploads.md)** - Image upload and retrieval
- **[Food API Guide](docs/api/food.md)** - AI nutrition detection
- **[Frontend Integration](docs/guides/frontend-integration.md)** - Frontend implementation guide
- **[Deployment Guide](docs/guides/deployment.md)** - Production deployment

## Technology Stack

- **Framework**: Flask 3.1.1
- **Database**: MySQL with SQLAlchemy ORM
- **Authentication**: JWT (Flask-JWT-Extended)
- **Password Security**: Bcrypt
- **AI Integration**: OpenAI GPT-4o Vision
- **Data Validation**: Marshmallow
- **File Upload**: Werkzeug

## Project Structure

```
trackamate_be/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Marshmallow schemas
│   └── views/                # Route handlers
│       ├── auth/             # Authentication endpoints
│       ├── burn/             # Burn endpoints
│       ├── commit/           # Commit endpoints
│       ├── food/             # Food tracking endpoints
│       ├── income/           # Income endpoints
│       ├── invest/           # Investment endpoints
│       └── utils/            # Shared utilities
├── docs/                     # Documentation
├── uploads/                  # Uploaded images
│   ├── burn/
│   ├── invest/
│   ├── commit/
│   └── food/
├── config.py                 # Configuration
├── run.py                    # Application entry point
├── setup_db.py              # Database initialization
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables (not in git)
```

## Core Concepts

### Salary Cycle (25th to 24th)

TracKaMate uses a unique salary cycle that runs from the 25th of one month to the 24th of the next month. All financial tracking and pool calculations are based on this cycle.

Example:
- Current date: Jan 15, 2024 → Cycle: Dec 25, 2023 to Jan 24, 2024
- Current date: Jan 30, 2024 → Cycle: Jan 25, 2024 to Feb 24, 2024

### Income Pool Allocation

When income is added, it's automatically split into three pools:
- **Burn Pool**: 20% (discretionary spending)
- **Invest Pool**: 30% (investments)
- **Commit Pool**: 50% (committed expenses, bills, food)

Example for RM 5000 income:
- Burn: RM 1000
- Invest: RM 1500
- Commit: RM 2500

## Development

### Running Tests
```bash
# TODO: Add test commands
pytest
```

### Database Migrations
```bash
python setup_db.py
```

### Environment Variables
Required environment variables in `.env`:
- `SECRET_KEY` - Flask session security
- `JWT_SECRET_KEY` - JWT token signing
- `DATABASE_URI` - MySQL connection string
- `OPENAI_API_KEY` - OpenAI API key for food analysis

## Security

- Passwords hashed with bcrypt
- JWT token-based authentication
- File type validation for uploads
- SQL injection prevention via SQLAlchemy ORM
- CORS configuration for frontend integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues or questions:
- Review the [documentation](docs/)
- Check the [development guide](DEVELOPMENT.md)
- Refer to Flask docs: https://flask.palletsprojects.com/
- SQLAlchemy docs: https://docs.sqlalchemy.org/

## Roadmap

- [ ] Add pagination to list endpoints
- [ ] Implement refresh tokens
- [ ] Add email notifications for reminders
- [ ] Implement data export (CSV, PDF)
- [ ] Add analytics and reporting endpoints
- [ ] Cloud storage integration (S3, GCS)
- [ ] Admin panel for user management
- [ ] Mobile app integration

---

**Version**: 1.1.0
**Last Updated**: October 2025
**Author**: TracKaMate Development Team
