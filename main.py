from dotenv import load_dotenv
load_dotenv()

from database import initialize_database
from frontend import run_app

initialize_database()
run_app()