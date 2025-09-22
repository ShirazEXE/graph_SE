'''
Pipeline: 
1) Query a SearXNG instance and return the top results
2) Scrape with Trafilatura
3) Summarise using transformers
4) Finally we aggregate it all. 

'''

import requests
import trafilatura
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import re

SEARXNG_URL = "http://localhost:8181/" # Self Hosted SearXNG Instance

#MODEL_NAME = "mosaicml/mpt-7b-instruct" 
#MODEL_NAME = "microsoft/phi-2" 
#MODEL_NAME = "mosaicml/mpt-7b-8k-instruct"  # For longer context(8k tokens)
#MODEL_NAME = "TheBloke/MPT-7B-Instruct-GGML"
#MODEL_NAME = "distilgpt2"
#MODEL_NAME = "facebook/bart-large-cnn"
#MODEL_NAME = "cognitivecomputations/dolphin-2.8-mistral-7b-v02" # Will test other Models later

#Loading Model and Tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# Adding pad token if missing 
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map="auto")

summarizer = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=512, # test and adjust according to model context later
    do_sample=False, # greedy decoding for deterministically selecting the most probable token at each step (if True then sampling-based approach: More Creativity/Randomness)
    pad_id_token = tokenizer.pad_token_id, # pad token to avoid warnings
    return_full_text=False # Only return generated text, not prompt
)

def search_web(query, num_results=15):
    params = {
        "q": query,
        "format": "json",
        "categories": "general",
        "language": "en",
    }

    response = requests.get(SEARXNG_URL, params=params)
    response.raise_for_status() # if searching fails throw error
    data = response.json()

    # Extracting the essential top results
    results = []

    # Loops through the top results(limited) and extracts all the necessary content using trafilatura
    for items in data.get("results", [])[:num_results]: 
        url = items.get("url")
        title = items.get("title")
        content = items.get("content")

        #Scraping full content from each page
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            full_text = trafilatura.extract(downloaded)
        else:
            full_text = content or ""

        # Storing scraped data to the results hashmap
        results.append({
            "title": title,
            "url": url,
            "content": full_text
        })

    return results

def summarize_entity(results):
    '''
    Takes the list of scraped results from search_web() function
    and returns a single, coherent and relevant summary for the search.
    '''

    # Aggregating all content
    all_text = "\n\n".join([r["content"] for r in results if r["content"]])

    #Deduplicating sentences
    sentences = re.split(r'(?<=[.!?])\s+', all_text)
    # Removing minute fragments and duplicates
    seen = set()
    clean_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 15 and sentence not in seen: # Filtering very short fragments
            clean_sentences.append(sentence)
            seen.add(sentence)

    deduplicated = ". ".join(clean_sentences)

    # Text chunking (making sure we chunk at sentence boundaries to avoid cutting mid-sentence)
    max_chunk_size = 2000 # will tune the number of characters per chunk during test
    chunks = []
    current_chunk = ""

    for sentence in clean_sentences:
        if len(current_chunk) + len(sentence) > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                chunks.append(sentence[:max_chunk_size]) # this handles very long sentences
                current_chunk = sentence[max_chunk_size:] if len(sentence) > max_chunk_size else ""
        else:
            current_chunk += ". " + sentence if current_chunk else sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())

    # Summarizing each chunk 
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk: {i+1}/{len(chunks)}")

    #     prompt = (
    #     "You are an expert information synthesizer. Create a comprehensive, well-structured summary from the following web-scraped content.\n\n"
        
    #     "INSTRUCTIONS:\n"
    #     "• Synthesize information from multiple sources into a coherent narrative\n"
    #     "• Prioritize the most current, authoritative, and relevant information\n"
    #     "• Preserve ALL factual data: numbers, percentages, dates, currencies, units of measurement, formulas, statistics, and technical specifications\n"
    #     "• Eliminate redundant information that appears across multiple sources\n"
    #     "• Resolve conflicting information by noting discrepancies or favoring more recent/authoritative sources\n"
    #     "• Organize content logically with clear sections and smooth transitions\n"
    #     "• Include specific examples, case studies, or applications where mentioned\n"
    #     "• Maintain technical accuracy while ensuring readability\n\n"
        
    #     "FORMAT REQUIREMENTS:\n"
    #     "• Use clear headings to organize different aspects of the topic\n"
    #     "• Present numerical data in context (e.g., '25% increase from 2022 to 2023' rather than just '25%')\n"
    #     "• Include timeframes and sources when data points are mentioned\n"
    #     "• Use bullet points sparingly, only for lists of specifications or key points\n"
    #     "• Write in complete sentences with proper flow between ideas\n\n"
        
    #     "QUALITY CHECKS:\n"
    #     "• Ensure no important data points are omitted\n"
    #     "• Verify that similar information from different sources is consolidated\n"
    #     "• Check that the summary provides actionable insights, not just facts\n"
    #     "• Confirm that technical terms are explained when first introduced\n\n"
        
    #     "Content to summarize:\n\n"
    #     f"{chunk}"
    # )

    # prompt = (
    #         "Summarize the following text into a coherent, readable summary.\n"
    #         "Preserve all numbers, units, formulas, dates, currency values, and other data.\n"
    #         "Remove redundant sentences if already mentioned in other parts.\n\n"
    #         f"{chunk}"
    # )

    prompt = f"Summarize the following text concisely, removing redundancy and preserving key facts, formulas, values and numbers:\n\n{chunk}\n\nSummary:"
        
    try:
        result = summarizer(prompt, max_new_tokens=300, temperature=0.3)
        #extracting only the generated text and cleaning it
        summary = result[0]['generated_text'].strip()

        # Handling any remaining prompt repetition
        if "Summary" in summary:
            summary = summary.split("Summary:")[-1].strip()
        if "summarize" in summary.lower()[:50]: # handles if the prompt leaks to the generated text at start
            lines = summary.split('\n')
            summary = '\n'.join([line for line in lines if not lines.lower().startswith(('summarize', 'preserve', 'remove'))])
        
        if summary and len(summary) > 10: # Making sure only non-empty and long enough chunk summaries are included
            chunk_summaries.append(summary)
        

    except Exception as e:
        print(f"Error summarizing chunk {i+1}: {e}")
        # if summarisation fails, we will use the first few lines as fallback
        fallback = ". ".join(chunk.split(". ")[:3])
        if fallback:
            chunk_summaries.append(fallback)


    final_summary = " ".join(chunk_summaries)

    #Removing any repetitive phrases
    final_summary = re.sub(r'(\b\w+\b(?:\s+\b\w+\b){0,5})\s+\1', r'\1', final_summary)


    return final_summary



