import logging
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("datamanager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataManager:
    """
    A singleton class that manages data exchange between modules with thread safety.
    Uses only in-memory dictionaries for data storage.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DataManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize data structures and locks for thread safety"""
        # Model data
        self.example_model = None
        self.target_model = None
        
        # Content data with locks for thread safety
        self.target_descriptions = {}
        self._descriptions_lock = threading.RLock()
        
        logger.info("DataManager initialized")
    
    def set_models(self, example_model, target_model):
        """Set the example and target models"""
        self.example_model = example_model
        self.target_model = target_model
        logger.info(f"Models set: Example={example_model}, Target={target_model}")
        
        # Import here to avoid circular imports
        import TelegramInteraction
        TelegramInteraction.example_model = example_model
        TelegramInteraction.target_model = target_model
    
    def get_target_model(self):
        """Get the current target model"""
        # Try to get from instance first
        if self.target_model:
            return self.target_model
            
        # Fall back to TelegramInteraction if needed
        try:
            import TelegramInteraction
            if hasattr(TelegramInteraction, 'target_model') and TelegramInteraction.target_model:
                self.target_model = TelegramInteraction.target_model
                return self.target_model
        except:
            pass
            
        return None
    
    def set_target_descriptions(self, descriptions):
        """Thread-safe setter for target descriptions"""
        with self._descriptions_lock:
            self.target_descriptions = descriptions
            logger.info(f"Updated target descriptions ({len(descriptions)} items)")
            
            # Also update TelegramInteraction for backward compatibility
            try:
                import TelegramInteraction
                TelegramInteraction.target_descriptions = descriptions
            except Exception as e:
                logger.error(f"Error updating TelegramInteraction: {e}")
    
    def get_target_descriptions(self):
        """Thread-safe getter for target descriptions"""
        with self._descriptions_lock:
            # If we have descriptions already, return them
            if self.target_descriptions:
                return self.target_descriptions.copy()  # Return a copy to prevent accidental modification
                
            # Otherwise try to get from TelegramInteraction
            try:
                import TelegramInteraction
                if hasattr(TelegramInteraction, 'target_descriptions') and TelegramInteraction.target_descriptions:
                    self.target_descriptions = TelegramInteraction.target_descriptions
                    return self.target_descriptions.copy()
            except:
                pass
                
            # Return empty dict if all else fails
            return {}
    
    def update_description(self, key, content):
        """Update a specific description with thread safety"""
        with self._descriptions_lock:
            self.target_descriptions[key] = content
            logger.info(f"Updated description: {key}")
    
    def clear_data(self):
        """Clear all data"""
        with self._descriptions_lock:
            self.target_descriptions = {}
            self.example_model = None
            self.target_model = None
            
            # Also clear TelegramInteraction for backward compatibility
            try:
                import TelegramInteraction
                TelegramInteraction.target_descriptions = {}
                TelegramInteraction.target_model = None
                TelegramInteraction.example_model = None
            except:
                pass
        
        logger.info("All data cleared")

    def analyze_content_sizes(self):
        """Analyze the size of content in target descriptions."""
        with self._descriptions_lock:
            sizes = {}
            large_descriptions = []
            total_size = 0
            for key, content in self.target_descriptions.items():
                size = len(content)
                sizes[key] = size
                total_size += size
                if size > 50000:  # Consider anything over ~50KB as large
                    large_descriptions.append((key, size))
            
            # Log the analysis
            logger.info(f"Content size analysis: {len(self.target_descriptions)} descriptions, {total_size} total characters")
            if large_descriptions:
                logger.warning(f"Found {len(large_descriptions)} large descriptions:")
                for key, size in large_descriptions:
                    logger.warning(f"  - {key}: {size} characters")
            
            return sizes, large_descriptions, total_size

    def validate_and_fix_content(self):
        """Validate descriptions and fix common issues."""
        with self._descriptions_lock:
            for key, content in list(self.target_descriptions.items()):
                # Check for excessively large content
                if len(content) > 100000:  # 100KB is very large for HTML content
                    logger.warning(f"Description '{key}' is very large ({len(content)} chars), truncating")
                    # Find a good breaking point
                    breaking_point = content.rfind('</li>', 0, 50000)
                    if breaking_point == -1:
                        breaking_point = content.rfind('</p>', 0, 50000)
                    if breaking_point == -1:
                        breaking_point = content.rfind('.', 0, 50000)
                    if breaking_point == -1:
                        breaking_point = 50000
                    
                    # Truncate and add note
                    self.target_descriptions[key] = content[:breaking_point] + "\n<!-- Content was truncated due to size limitations -->"
                    logger.warning(f"Truncated '{key}' from {len(content)} to {len(self.target_descriptions[key])} chars")
                
                # Check for and fix common HTML issues
                # 1. Unclosed tags
                if "<ol" in content and "</ol>" not in content:
                    logger.warning(f"Fixing unclosed <ol> tag in '{key}'")
                    self.target_descriptions[key] = content + "</ol>"
                
                if "<ul" in content and "</ul>" not in content:
                    logger.warning(f"Fixing unclosed <ul> tag in '{key}'")
                    self.target_descriptions[key] = content + "</ul>"
                
                # 2. Check for <html> tags in content (these should not be there)
                if "<html>" in content or "</html>" in content:
                    logger.warning(f"Removing <html> tags from '{key}'")
                    self.target_descriptions[key] = content.replace("<html>", "").replace("</html>", "")
                
                # 3. Ensure content starts with valid HTML
                if not content.strip().startswith("<"):
                    logger.warning(f"Content in '{key}' does not start with HTML tag")
                    # If we're inside a code block, fix it
                    if content.strip().startswith("```html"):
                        logger.warning(f"Content in '{key}' contains code block markers, fixing")
                        clean_content = content.strip()
                        # Remove code block markers
                        clean_content = clean_content.replace("```html", "", 1)
                        if clean_content.endswith("```"):
                            clean_content = clean_content[:-3]
                        self.target_descriptions[key] = clean_content.strip()

    def split_large_description(self, key, max_size=40000):
        """Split a large description into multiple parts if needed."""
        with self._descriptions_lock:
            if key not in self.target_descriptions:
                logger.error(f"Description '{key}' not found")
                return False
                
            content = self.target_descriptions[key]
            if len(content) <= max_size:
                logger.info(f"Description '{key}' is not large enough to split")
                return False
            
            # Find good splitting points (end of sections or paragraphs)
            parts = []
            remaining = content
            part_num = 1
            
            while len(remaining) > max_size:
                # Try to find a good breaking point
                break_point = remaining.rfind('</li>', 0, max_size)
                if break_point == -1:
                    break_point = remaining.rfind('</p>', 0, max_size)
                if break_point == -1:
                    break_point = remaining.rfind('</div>', 0, max_size)
                if break_point == -1:
                    break_point = remaining.rfind('.', 0, max_size)
                if break_point == -1:
                    break_point = max_size
                
                # Add part header/footer
                part_content = remaining[:break_point + 1]
                if part_num > 1:
                    part_content = f"<p><em>Part {part_num} continued from previous section</em></p>\n" + part_content
                
                parts.append(part_content)
                remaining = remaining[break_point + 1:]
                part_num += 1
            
            # Add the last part
            if remaining:
                if part_num > 1:
                    remaining = f"<p><em>Part {part_num} continued from previous section</em></p>\n" + remaining
                parts.append(remaining)
            
            # Update the descriptions dictionary
            if part_num > 1:
                # Create new keys for parts
                self.target_descriptions.pop(key)
                for i, part_content in enumerate(parts):
                    new_key = f"{key} (Part {i+1}/{len(parts)})"
                    self.target_descriptions[new_key] = part_content
                    logger.info(f"Created part {i+1}/{len(parts)} for '{key}' with {len(part_content)} chars")
                
                return True
            
            return False

    def prepare_descriptions_for_publishing(self):
        """Prepare all descriptions for publishing by fixing/validating content."""
        logger.info("Preparing descriptions for publishing...")
        
        # Analyze content sizes first
        sizes, large_descriptions, total_size = self.analyze_content_sizes()
        
        # Validate and fix common issues
        self.validate_and_fix_content()
        
        # Split very large descriptions if needed
        split_count = 0
        if large_descriptions:
            for key, size in large_descriptions:
                if size > 50000:  # Only split if really necessary
                    if self.split_large_description(key):
                        split_count += 1
        
        if split_count > 0:
            logger.info(f"Split {split_count} large descriptions into parts")
        
        # Final analysis after all fixes
        final_sizes, final_large, final_total = self.analyze_content_sizes()
        
        logger.info(f"Descriptions prepared: {len(self.target_descriptions)} descriptions, {final_total} total characters")
        return len(self.target_descriptions)

# Create a global instance
data_manager = DataManager()