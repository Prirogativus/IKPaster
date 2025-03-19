import anthropic
import os
import DataExtractor
import ContentPublisher

publisher = ContentPublisher
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

  data = DataExtractor.DataExtractorClass()
  
  for key in data.example_descriptions:
      input_text = data.example_descriptions[key]
      message = aimodel.messages.create(
          model="claude-3-7-sonnet-20250219",
          max_tokens=2000,
          temperature=0.4,
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
      publisher.target_descriptions[key] = message
