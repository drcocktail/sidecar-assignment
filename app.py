# In app.py

import orchestrator # This is our renamed main.py
import time

def main():
    """
    Main application loop to interact with the user and run the tracking agent.
    """
    print("--- Welcome to the AI-Powered Shipment Tracker ---")
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


if __name__ == "__main__":
    main()