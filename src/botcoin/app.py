import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("Hello from your project!")
    print("API_KEY:", os.getenv("API_KEY"))
    return True

if __name__ == "__main__":
    main()