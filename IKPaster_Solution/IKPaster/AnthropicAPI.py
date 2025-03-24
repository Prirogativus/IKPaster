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
    
    # Escape HTML variables like {{image1}} to \{\{image1\}\}
    def escape_html_variables(content):
        import re
        pattern = r'\{\{([^}]+)\}\}'
        escaped_content = re.sub(pattern, r'\\{\\{\1\\}\\}', content)
        return escaped_content
    
    try:
        # Escape HTML variables before sending to Anthropic API
        processed_input = escape_html_variables(input_text)
        logger.info(f"HTML variables escaped in '{description_name}' before API processing")
        
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
                            "text": processed_input
                        }
                    ]
                }
            ]
        )
        
        processed_content = message.content[0].text
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
            if key == 'Codes':
                processed_descriptions[key] = processed_content
                data_manager.update_description(key, processed_content)
                continue
            
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
        
        logger.info(f"Successfully processed {len(processed_descriptions)} descriptions")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in get_target_text: {e}")
        return False