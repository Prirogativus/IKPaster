import anthropic
import os
import logging
import TelegramInteraction

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

def get_target_text():
    """
    Process the extracted content from TelegramInteraction.target_descriptions 
    and store the reformatted content back in the same dictionary.
    """
    try:
        logger.info("Starting Anthropic API content processing")
        
        # Get the descriptions from TelegramInteraction
        if not hasattr(TelegramInteraction, 'target_descriptions') or not TelegramInteraction.target_descriptions:
            logger.error("No target_descriptions found in TelegramInteraction")
            return False
        
        descriptions = TelegramInteraction.target_descriptions
        logger.info(f"Found {len(descriptions)} descriptions to process")
        
        # Initialize a new dictionary to store processed content
        processed_descriptions = {}
        
        # Process each description
        for key, input_text in descriptions.items():
            logger.info(f"Processing description: {key}")
            
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
                
                # Store the reformatted content
                processed_content = message.content[0].text
                processed_descriptions[key] = processed_content
                logger.info(f"Successfully processed description: {key}")
                
            except Exception as e:
                logger.error(f"Error processing description '{key}': {e}")
                # If processing fails for one description, continue with others
                continue
        
        # Update TelegramInteraction with processed descriptions
        TelegramInteraction.target_descriptions = processed_descriptions
        logger.info(f"Successfully processed {len(processed_descriptions)} descriptions")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in get_target_text: {e}")
        return False

# For standalone testing
if __name__ == "__main__":
    # Set up test data if running independently
    if not hasattr(TelegramInteraction, 'target_descriptions') or not TelegramInteraction.target_descriptions:
        TelegramInteraction.target_descriptions = {
            "Hard Reset": "<p>This is a sample reset description for testing.</p>",
            "Developer Options": "<p>This is how to enable developer options.</p>"
        }
        print("Set up test data for Anthropic API processing")
    
    # Run the processing
    success = get_target_text()
    
    if success:
        print("Anthropic API processing completed successfully")
        # Print processed content
        for key, value in TelegramInteraction.target_descriptions.items():
            print(f"\n---{key}---")
            print(value[:100] + "..." if len(value) > 100 else value)
    else:
        print("Anthropic API processing failed")