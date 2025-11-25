# TrackMyCash

#### Video Demo: <https://www.youtube.com/watch?v=dNberLYoAN4>

#### Description:
TrackMyCash is a web-based application that helps users record income and expenses, visualize monthly summaries, and manage recurring financial obligations like loans (EMIs) and insurance premiums. It emphasizes a clean UI and a simple flow: register, log in, add transactions, and review a dashboard that aggregates data for the current month.

The application is built with Flask, SQLAlchemy, and Flask-Login. Data is stored in SQLite and initialized automatically on first run. Users can create their own custom categories while also having access to a set of global defaults. The dashboard shows totals for the current month, a recent transactions list, category breakdown (for rendering in the UI), and the combined monthly burden of active loans and insurance premiums.

Authentication is implemented via Flask-Login, with secure password hashing. The application uses the application-factory pattern for clarity and easier testing. UI templates are organized with a `base.html` layout and section-specific templates.

This project builds upon CS50 concepts: HTTP, templating, state management, SQL, and security best practices. It also demonstrates practical patterns for creating CRUD pages, with form handling, validation, and flash messaging.

#### Distinctiveness and Complexity:
- Web app with persistent authentication and per-user data segregation
- Multiple related models (`User`, `Transaction`, `Category`, `Loan`, `Insurance`) and relationships
- Seeded global categories with uniqueness constraints scoped by user and type
- Monthly calculations (summing income/expense, EMI totals, premium totals) and date handling
- Modular structure with an application factory and blueprint-like route grouping in a single file for simplicity

#### How to Run:
1. Ensure Python 3.10+ is installed.
2. In a terminal, navigate to the `project/` directory.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the server:
   ```bash
   python app.py
   ```
5. Open your browser at `http://localhost:5000`.

On first run, the app will create `budget_tracker.db` in the `instance/` folder and seed default categories.

#### Files Created and Their Roles:
- `app.py`: Main Flask application using the application factory pattern. Defines models (`User`, `Category`, `Transaction`, `Loan`, `Insurance`), initializes the database, seeds default categories, and registers all routes: authentication, dashboard, transactions, categories API, loans, and insurances.
- `requirements.txt`: Pinning core dependencies: Flask, Flask-Login, Flask-SQLAlchemy, SQLAlchemy, python-dateutil, Werkzeug.
- `templates/`: Jinja2 templates for all pages.
  - `base.html`: Layout and shared UI. Loads Bootstrap and CSS.
  - `login.html`, `register.html`: Auth pages.
  - `dashboard.html`: Monthly overview with totals and lists.
  - `transactions/form.html`, `transactions/list.html`: CRUD for transactions.
  - `loans/form.html`, `loans/list.html`: CRUD and EMI payment for loans.
  - `insurances/form.html`, `insurances/list.html`: CRUD and premium payment for insurances.
- `static/css/style.css`: Custom styles.
- `instance/`: Runtime folder where `budget_tracker.db` is created automatically. This folder is not required for import but is used by Flask to store instance data.

Removed from submission to avoid confusion:
- `project.py` (Tkinter desktop GUI) – not part of the web submission path.
- Prebuilt SQLite files – the app will initialize a fresh database.

#### Design Choices:
- Application factory (`create_app`) allows better separation of configuration and simplifies testing. It also ensures tables and seeds are created at startup in a controlled context.
- Authentication uses Flask-Login with a user loader and secure password hashing from Werkzeug.
- Categories include both global and user-specific items, with a uniqueness constraint across `(name, type, user_id)` to prevent duplicates.
- Loans and insurances are tracked with next-due dates and helper properties for monthly calculations. Actions like paying an EMI or a premium also insert expense transactions for a unified ledger.
- Simplicity over microservices or blueprints for this project size; all routes live in a single module for ease of review.

#### Notes:
- Cite of AI tools: Portions of scaffolding, text, and organization were assisted by AI-based tooling; all custom logic, integration decisions, and final implementation were authored and verified by me.
- For production, set `SECRET_KEY` via environment variable and consider a production database engine.

#### Acknowledgements:
Thanks to CS50 for the curriculum and guidance.