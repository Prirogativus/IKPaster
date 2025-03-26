import json
import os

def generate_configs(num_instances, base_path="instances"):
    """
    Generate configuration files for multiple instances.
    
    Args:
        num_instances: Number of instances to generate configs for
        base_path: Base directory for instance configs
    """
    print(f"Generating configurations for {num_instances} instances...")
    
    # Create base directory if it doesn't exist
    os.makedirs(base_path, exist_ok=True)
    
    for i in range(1, num_instances + 1):
        instance_dir = os.path.join(base_path, f"instance_{i}")
        os.makedirs(instance_dir, exist_ok=True)
        
        # Prompt for instance-specific configuration
        print(f"\nConfiguration for Instance {i}:")
        telegram_token = input(f"Enter Telegram Bot Token for Instance {i}: ")
        username = input(f"Enter admin username (default: Istomin): ") or "Istomin"
        password = input(f"Enter admin password (default: VnXJ7i47n4tjWj&g): ") or "VnXJ7i47n4tjWj&g"
        anthropic_api_key = input(f"Enter Anthropic API key for Instance {i}: ")
        
        # Create config dictionary
        config = {
            "instance_id": i,
            "telegram_token": telegram_token,
            "admin_credentials": {
                "username": username,
                "password": password
            },
            "anthropic_api_key": anthropic_api_key,
            "log_dir": os.path.join(instance_dir, "logs")
        }
        
        # Create log directory
        os.makedirs(config["log_dir"], exist_ok=True)
        
        # Write config to file
        config_path = os.path.join(instance_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        
        print(f"Configuration for Instance {i} saved to {config_path}")

if __name__ == "__main__":
    try:
        num_instances = int(input("How many instances do you want to configure? "))
        generate_configs(num_instances)
        print("\nConfiguration generation complete!")
    except ValueError:
        print("Please enter a valid number.")
    except Exception as e:
        print(f"An error occurred: {e}")