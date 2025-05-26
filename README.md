## Getting Started

### Prerequisites
- Python 3.11 (do not use 3.12)
- Django (latest version)

### Installation

To set up the To-Do App Basic on your local machine, follow these steps:

1. **Clone the Repository**
   ```bash
   git clone https://github.com/johurul000/actionboard_backend
   cd actionboard_backend
   ```

2. **Set Up a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Start the Server**
   ```bash
   python manage.py runserver
   ```

   Visit `http://127.0.0.1:8000/` in your browser.
