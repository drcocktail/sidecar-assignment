import os
import sys
import subprocess
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible (3.8+)"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required.")
        print(f"   Current version: {sys.version}")
        return False
    else:
        print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_and_create_env_file():
    """Check if .env file exists and has required keys, create if needed"""
    env_path = Path(".env")
    required_keys = ["GOOGLE_API_KEY"]
    
    if not env_path.exists():
        print("❌ .env file not found.")
        create_env = input("Would you like to create a .env file now? (y/n): ").lower().strip()
        if create_env in ['y', 'yes']:
            return setup_env_file(env_path, required_keys)
        else:
            print("Cannot proceed without .env file. Exiting...")
            return False
    
    # Check if .env has required keys
    missing_keys = []
    try:
        with open(env_path, 'r') as f:
            content = f.read()
            for key in required_keys:
                if f"{key}=" not in content or f'{key}=""' in content or f"{key}=''" in content:
                    missing_keys.append(key)
        
        if missing_keys:
            print(f"❌ Missing or empty keys in .env: {', '.join(missing_keys)}")
            fix_env = input("Would you like to update the .env file? (y/n): ").lower().strip()
            if fix_env in ['y', 'yes']:
                return setup_env_file(env_path, missing_keys, update=True)
            else:
                print("Cannot proceed without proper .env configuration. Exiting...")
                return False
        
        print("✅ .env file found and configured properly")
        return True
        
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False

def setup_env_file(env_path, keys_to_setup, update=False):
    """Create or update .env file with required keys"""
    print(f"\n{'Updating' if update else 'Creating'} .env file...")
    
    existing_content = ""
    if update and env_path.exists():
        with open(env_path, 'r') as f:
            existing_content = f.read()
    
    new_entries = []
    for key in keys_to_setup:
        if key == "GOOGLE_API_KEY":
            print(f"\nTo use this application, you need a Google AI API key.")
            print("You can get one from: https://aistudio.google.com/app/apikey")
            api_key = input(f"Enter your {key}: ").strip()
            if not api_key:
                print(f"❌ {key} cannot be empty")
                return False
            new_entries.append(f"{key}={api_key}")
    
    try:
        mode = 'a' if update else 'w'
        with open(env_path, mode) as f:
            if update and existing_content and not existing_content.endswith('\n'):
                f.write('\n')
            for entry in new_entries:
                f.write(f"{entry}\n")
        
        print(f"✅ .env file {'updated' if update else 'created'} successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error writing .env file: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n--- Checking Dependencies ---")
    
    required_packages = []
    try:
        with open("requirements.txt", 'r') as f:
            required_packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False
    
    if not required_packages:
        print("⚠️  No dependencies specified in requirements.txt")
        return True
    
    missing_packages = []
    for package in required_packages:
        package_name = package.split('==')[0].split('>=')[0].split('<=')[0]
        try:
            __import__(package_name.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        install_deps = input("Would you like to install missing dependencies? (y/n): ").lower().strip()
        if install_deps in ['y', 'yes']:
            return install_dependencies()
        else:
            print("Cannot proceed without required dependencies. Exiting...")
            return False
    
    print("✅ All dependencies are installed")
    return True

def install_dependencies():
    """Install dependencies from requirements.txt"""
    print("\n--- Installing Dependencies ---")
    try:
        print("Installing packages...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Installation timed out")
        return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def test_api_connection():
    """Test if the API key works by making a simple request"""
    print("\n--- Testing API Connection ---")
    try:
        from dotenv import load_dotenv
        import google.generativeai as genai
        
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            print("❌ GOOGLE_API_KEY not found in environment")
            return False
        
        genai.configure(api_key=api_key)
        
        # Test with a simple request
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hello")
        
        if response.text:
            print("✅ API connection successful")
            return True
        else:
            print("❌ API connection failed - no response")
            return False
            
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        print("Please check your API key and try again")
        return False

def run_setup():
    """Run all setup checks"""
    print("=== AI-Powered Shipment Tracker Setup ===\n")
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check .env file
    if not check_and_create_env_file():
        return False
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Test API connection
    if not test_api_connection():
        return False
    
    print("\n✅ Setup completed successfully!")
    print("=" * 50)
    return True

def main():
    """
    Main application loop to interact with the user and run the tracking agent.
    """
    # Run setup checks first
    if not run_setup():
        print("\n❌ Setup failed. Please resolve the issues above and try again.")
        sys.exit(1)
    
    # Import here after setup is complete
    try:
        import orchestrator
    except ImportError as e:
        print(f"❌ Error importing orchestrator: {e}")
        sys.exit(1)
    
    print("\n--- Welcome to the AI-Powered Shipment Tracker ---")
    print("Enter a Booking ID to track, or type 'quit' to exit.")

    while True:
        booking_id = input("\nEnter Booking ID: ")

        if booking_id.lower() == 'quit':
            print("Thank you for using the tracker. Goodbye!")
            break

        if not booking_id:
            print("Please enter a valid Booking ID.")
            continue
            
        print(f"\nInitiating tracking for ID: {booking_id}...")
        
        # Call the orchestrator to do the heavy lifting
        # The orchestrator will decide whether to use the Agent or Executor
        start_time = time.time()
        try:
            result = orchestrator.run_task(booking_id=booking_id, carrier="HMM")
            end_time = time.time()

            print("\n--- Tracking Result ---")
            if result:
                # Assuming result is a dictionary like {'voyage_number': '...', 'arrival_date': '...'}
                for key, value in result.items():
                    print(f"{key.replace('_', ' ').title()}: {value}")
            else:
                print("Sorry, we were unable to retrieve the tracking information.")
            
            print(f"-----------------------")
            print(f"(Task completed in {end_time - start_time:.2f} seconds)")
        
        except Exception as e:
            print(f"❌ Error during tracking: {e}")
            print("Please try again or contact support.")


if __name__ == "__main__":
    main()