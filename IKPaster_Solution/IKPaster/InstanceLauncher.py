import os
import sys
import json
import shutil
import subprocess
import time

def create_instance(instance_id, base_dir="instances", telegram_token=None):
    """
    Create a new instance directory with its own configuration.
    
    Args:
        instance_id: ID number for this instance
        base_dir: Base directory for all instances
        telegram_token: Telegram bot token for this instance
    
    Returns:
        The path to the instance directory
    """
    # Create instance directory
    instance_dir = os.path.join(base_dir, f"instance_{instance_id}")
    os.makedirs(instance_dir, exist_ok=True)
    
    # Create logs directory
    logs_dir = os.path.join(instance_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # If no token is provided, ask for it
    if not telegram_token:
        telegram_token = input(f"Enter Telegram bot token for Instance {instance_id}: ")
    
    # Create config file
    config = {
        "instance_id": instance_id,
        "telegram_token": telegram_token,
        "admin_credentials": {
            "username": "Istomin",
            "password": "VnXJ7i47n4tjWj&g"
        },
        "anthropic_api_key": input(f"Enter Anthropic API key for Instance {instance_id}: "),
        "log_dir": logs_dir
    }
    
    config_path = os.path.join(instance_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    
    print(f"Created configuration for Instance {instance_id}")
    
    # Copy all Python files to the instance directory
    python_files = [f for f in os.listdir(".") if f.endswith(".py")]
    for file in python_files:
        shutil.copy(file, instance_dir)
    
    print(f"Copied Python files to Instance {instance_id} directory")
    
    return instance_dir

def launch_instance(instance_dir):
    """
    Launch the IKPaster application in the specified instance directory.
    
    Args:
        instance_dir: Path to the instance directory
    
    Returns:
        The subprocess object
    """
    # Change to the instance directory
    os.chdir(instance_dir)
    
    # Create a batch file to run the instance
    batch_file = "run_instance.bat"
    with open(batch_file, "w") as f:
        f.write("@echo off\n")
        f.write(f"echo Starting IKPaster Instance in {instance_dir}\n")
        f.write(f"python -u IKPaster.py\n")
        f.write("pause\n")
    
    # Launch the batch file in a new window
    process = subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", batch_file])
    
    # Change back to the original directory
    os.chdir("../..")
    
    return process

def main():
    """Main function to set up and launch multiple instances."""
    print("===== IKPaster Multi-Instance Launcher =====")
    
    # Create base directory
    base_dir = "instances"
    os.makedirs(base_dir, exist_ok=True)
    
    # Ask how many instances to create
    try:
        num_instances = int(input("How many instances do you want to create and run? "))
        if num_instances <= 0:
            print("Number of instances must be greater than 0.")
            return
    except ValueError:
        print("Please enter a valid number.")
        return
    
    # Create and launch each instance
    processes = []
    for i in range(1, num_instances + 1):
        print(f"\n----- Setting up Instance {i} -----")
        
        # Create the instance
        instance_dir = create_instance(i, base_dir)
        
        # Launch the instance
        print(f"Launching Instance {i}...")
        process = launch_instance(instance_dir)
        processes.append(process)
        
        # Wait a bit between launches to avoid conflicts
        time.sleep(2)
    
    print(f"\n===== {num_instances} instances launched successfully =====")
    print("Close this window when you're done with all instances.")
    
    # Wait for the processes (optional, since they're detached)
    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("Launcher interrupted.")

if __name__ == "__main__":
    main()