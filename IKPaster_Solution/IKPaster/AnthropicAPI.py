import anthropic
import os
import logging
import TelegramInteraction
from DataManager import data_manager  # Import the data manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("anthropic.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_KEY = ""
aimodel = anthropic.Anthropic(api_key=API_KEY)

sys_prompt = """You are an expert at reformatting device instruction content. For each set of instructions provided, you must:

1. ALWAYS do TWO things:
   - Completely rephrase the text to make it fresh while maintaining the core steps and meaning
   - Apply proper formatting according to specific rules

2. Formatting rules:
   - Use <span style="font-weight:bold;"> for interface elements and sentence accent words (buttons, menus, options)
   - Use <strong> for searchable terms (device names, features, technical terms)
   - Bold any punctuation (periods, commas) directly adjacent to bolded text using the<span style>
   - Create HTML tables for adjacent images with this format:
     <table border="0" cellpadding="1" cellspacing="1" class="table-img">
       <tbody>
         <tr>
           <td>{{image1}}</td>
           <td>{{image2}}</td>
         </tr>
       </tbody>
     </table>

3. Content guidelines:
   - Keep language straightforward but vary phrasing between instruction sets
   - Avoid overly technical language unless in the original
   - Include congratulatory messages within the final list item, not as a separate item
   - Use ordered lists <ol> for step-by-step instructions
   - Preserve all image placeholders exactly as provided ({{image1}}, {{images.123456}})
   - Preserve all original headings exactly as provided

4. Implementation process:
   - Analyze the original content to identify interface elements and searchable terms
   - Completely rephrase while maintaining core steps
   - Apply proper formatting to all elements
   - Ensure tables have border="0" attribute
   - Maintain ordered list structure
   - Include congratulatory messages within final steps
   - Preserve all image placeholders

Provide the complete reformatted HTML in a single code block that can be copied directly for website implementation. The code should be ready to paste without requiring modifications."""

def process_description(description_name, input_text):
    """
    Process a single description using Anthropic API.
    Returns the processed content as a string.
    """
    logger.info(f"Processing description: {description_name}")
    
    # Check if content has code block markers and remove them
    if input_text.strip().startswith("```html"):
        logger.info(f"Removing code block markers from '{description_name}'")
        input_text = input_text.strip().replace("```html", "", 1)
        if input_text.endswith("```"):
            input_text = input_text[:-3]
        input_text = input_text.strip()
    
    # Check for content too large for Anthropic API
    if len(input_text) > 90000:  # Anthropic has token limits
        logger.warning(f"Content for '{description_name}' is too large ({len(input_text)} chars), truncating")
        # Find a good breaking point
        breaking_point = input_text.rfind('</li>', 0, 80000)
        if breaking_point == -1:
            breaking_point = input_text.rfind('</p>', 0, 80000)
        if breaking_point == -1:
            breaking_point = input_text.rfind('.', 0, 80000)
        if breaking_point == -1:
            breaking_point = 80000
        
        # Truncate and add note
        input_text = input_text[:breaking_point] + "\n<!-- Content was truncated for API processing -->"
        logger.warning(f"Truncated '{description_name}' to {len(input_text)} chars for processing")
    
    try:
        # Call Anthropic API to reformat the content
        message = aimodel.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=2000,
            temperature=1,
            system=sys_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": input_text
                        }
                    ]
                }
            ]
        )
        
        # Get the processed content
        processed_content = message.content[0].text
        
        # Check if the response has code blocks and extract just the HTML
        if processed_content.strip().startswith("```html"):
            logger.info(f"Removing code block markers from API response for '{description_name}'")
            processed_content = processed_content.strip().replace("```html", "", 1)
            if processed_content.endswith("```"):
                processed_content = processed_content[:-3]
            processed_content = processed_content.strip()
        
        logger.info(f"Successfully processed description: {description_name}")
        
        return processed_content
        
    except Exception as e:
        logger.error(f"Error processing description '{description_name}': {e}")
        return None

def get_target_text():
    """
    Process the extracted content and store the reformatted content.
    Uses DataManager for thread-safe data exchange.
    """
    try:
        logger.info("Starting Anthropic API content processing")
        
        # Get the descriptions from DataManager
        descriptions = data_manager.get_target_descriptions()
        
        if not descriptions:
            logger.error("No target_descriptions found in DataManager")
            return False
        
        logger.info(f"Found {len(descriptions)} descriptions to process")
        
        # Initialize a new dictionary to store processed content
        processed_descriptions = {}
        
        # Process each description
        for key, input_text in descriptions.items():
            processed_content = process_description(key, input_text)
            
            if processed_content:
                # Store the processed content
                processed_descriptions[key] = processed_content
                
                # Optionally save each description as it's processed for fault tolerance
                data_manager.update_description(key, processed_content)
            else:
                # Keep the original content if processing failed
                logger.warning(f"Using original content for '{key}' due to processing failure")
                processed_descriptions[key] = input_text
        
        # Update the data manager with all processed descriptions
        data_manager.set_target_descriptions(processed_descriptions)
        
        # Save to file for persistence
        data_manager.save_descriptions_to_file()
        
        logger.info(f"Successfully processed {len(processed_descriptions)} descriptions")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in get_target_text: {e}")
        return False

def process_batch(descriptions_dict):
    """
    Process a batch of descriptions and return the processed results.
    This can be called directly by other modules.
    """
    try:
        logger.info(f"Processing batch of {len(descriptions_dict)} descriptions")
        
        results = {}
        for key, content in descriptions_dict.items():
            processed = process_description(key, content)
            if processed:
                results[key] = processed
                
        logger.info(f"Successfully processed batch of {len(results)} descriptions")
        return results
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        return {}

# For standalone testing
if __name__ == "__main__":
    # Set up test data if running independently
    if not data_manager.get_target_descriptions():
        test_data = {
            "Hard Reset": "<p>This is a sample reset description for testing.</p>",
            "Developer Options": "<p>This is how to enable developer options.</p>"
        }
        data_manager.set_target_descriptions(test_data)
        print("Set up test data for Anthropic API processing")
    
    # Run the processing
    success = get_target_text()
    
    if success:
        print("Anthropic API processing completed successfully")
        # Print processed content
        descriptions = data_manager.get_target_descriptions()
        for key, value in descriptions.items():
            print(f"\n---{key}---")
            print(value[:100] + "..." if len(value) > 100 else value)
    else:
        print("Anthropic API processing failed")