import os
import openai
import json
import time
import re
from tqdm import tqdm
import logging

# --- Configuration ---
API_KEY = os.getenv("OPENROUTER_API_KEY")  # OpenRouter API密钥
if not API_KEY:
    print("错误：请设置 OPENROUTER_API_KEY 环境变量")
    exit(1)
BASE_URL = "https://openrouter.ai/api/v1"
SVG_MODEL = "moonshotai/kimi-k2:free"
XHS_MODEL = "moonshotai/kimi-k2:free"

DATA_FILE = "twillot-public-post-sorted.json"
SVG_PROMPT_FILE = "svg提示词.txt"
XHS_PROMPT_FILE = "小红书文案提示词.txt"
OUTPUT_DIR = "output"

API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY_SECONDS = 5
API_CALL_INTERVAL_SECONDS = 4 # Interval between processing each record (OpenRouter限制: 60秒/16次 = 3.75秒)

# 全局变量跟踪最后API调用时间
_last_api_call = 0

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- OpenRouter API Client Setup ---
try:
    client = openai.OpenAI(
        api_key=API_KEY, 
        base_url=BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com",
            "X-Title": "TweetProcessor"
        }
    )
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")
    exit(1)

def call_openrouter_api(model, system_prompt, user_prompt):
    """Calls the OpenRouter API with retry mechanism and rate limiting."""
    global _last_api_call
    
    for attempt in range(API_RETRY_ATTEMPTS):
        try:
            # 检查API调用间隔（速度限制）
            current_time = time.time()
            if '_last_api_call' in globals():
                time_since_last = current_time - _last_api_call
                if time_since_last < API_CALL_INTERVAL_SECONDS:
                    wait_time = API_CALL_INTERVAL_SECONDS - time_since_last
                    logging.info(f"等待速度限制: {wait_time:.1f}秒")
                    time.sleep(wait_time)
            
            chat = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
            )
            
            # 更新最后调用时间
            _last_api_call = time.time()
            
            return chat.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                logging.warning(f"速度限制错误 (尝试 {attempt + 1}/{API_RETRY_ATTEMPTS}): {e}")
                # 429错误需要更长的等待时间
                if attempt < API_RETRY_ATTEMPTS - 1:
                    wait_time = 10 * (attempt + 1)  # 递增延迟：10, 20, 30秒
                    logging.info(f"速度限制，等待 {wait_time} 秒后重试")
                    time.sleep(wait_time)
                else:
                    logging.error(f"速度限制重试次数已达上限: {e}")
                    return None
            else:
                logging.warning(f"API调用失败 (尝试 {attempt + 1}/{API_RETRY_ATTEMPTS}) for model {model}. Error: {e}")
                if attempt < API_RETRY_ATTEMPTS - 1:
                    time.sleep(API_RETRY_DELAY_SECONDS)
                else:
                    logging.error(f"API调用失败 after {API_RETRY_ATTEMPTS} attempts.")
                    return None

def sanitize_filename(name):
    """Removes or replaces characters that are invalid in folder names."""
    name = re.sub(r'[\/*?":<>|]', "", name)
    name = name.replace(" ", "_")
    return name[:100] # Limit length

def parse_xiaohongshu_post(content):
    """Parses the Xiaohongshu post to extract title and body."""
    try:
        lines = content.strip().split('\n')
        title = ""
        body_lines = []
        
        # 处理API实际返回的格式：第一行是标题，可能有"2. 正文"标记
        if lines:
            # 第一行作为标题
            title = lines[0].strip()
            
            # 从第二行开始处理正文
            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                # 跳过"2. 正文"、"正文:"等标记行
                if line in ["2. 正文", "正文:", "Body:", "1. 标题", "标题:"]:
                    continue
                # 跳过空行
                if not line:
                    continue
                body_lines.append(line)
        
        body = '\n'.join(body_lines)
        
        if not title:
            title = "Untitled"
            logging.warning(f'Could not parse title. Using "Untitled". Full content received: "{content[:200]}..."')

        return title, body
    except Exception as e:
        logging.error(f"Exception during Xiaohongshu content parsing: {e}")
        return "Untitled", content # Return full content as body on error

def main():
    """Main processing loop."""
    # --- Load prompts and data ---
    try:
        with open(SVG_PROMPT_FILE, 'r', encoding='utf-8') as f:
            svg_system_prompt = f.read()
        with open(XHS_PROMPT_FILE, 'r', encoding='utf-8') as f:
            xhs_system_prompt = f.read()
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            tweets = json.load(f)
    except FileNotFoundError as e:
        logging.error(f"Required file not found: {e}. Please make sure '{DATA_FILE}', '{SVG_PROMPT_FILE}', and '{XHS_PROMPT_FILE}' exist.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    logging.info(f"Starting to process {len(tweets)} records.")
    
    for tweet in tqdm(tweets, desc="Processing Tweets"):
        full_text = tweet.get('full_text')
        tweet_id = tweet.get('id', 'unknown_id')

        if not full_text:
            logging.warning(f"Skipping record with ID {tweet_id} due to empty 'full_text'.")
            continue

        # --- Step 1: Generate Xiaohongshu copy to get the title ---
        logging.info(f"[ID: {tweet_id}] Generating Xiaohongshu copy...")
        xhs_content = call_openrouter_api(XHS_MODEL, xhs_system_prompt, full_text)
        
        if not xhs_content:
            logging.error(f"[ID: {tweet_id}] Failed to generate Xiaohongshu content. Skipping record.")
            continue
            
        title, body = parse_xiaohongshu_post(xhs_content)
        
        # --- Create directory (handles duplicates) ---
        # 从body的第一行提取文件夹名称
        body_lines = body.strip().split('\n')
        folder_title = body_lines[0].strip() if body_lines else f"tweet_{tweet_id}"
        sanitized_title = sanitize_filename(folder_title)
        record_dir = os.path.join(OUTPUT_DIR, sanitized_title)
        
        # Resume capability: Check if final file exists
        body_file_path = os.path.join(record_dir, 'body.txt')
        if os.path.exists(body_file_path):
            logging.info(f"[ID: {tweet_id}] Output already exists for title '{sanitized_title}'. Skipping.")
            continue

        # Handle folder name conflicts
        counter = 1
        while os.path.exists(record_dir):
            record_dir = os.path.join(OUTPUT_DIR, f"{sanitized_title}_{counter}")
            counter += 1
        
        os.makedirs(record_dir)

        # --- Step 2: Generate SVG ---
        logging.info(f"[ID: {tweet_id}] Generating SVG...")
        svg_code = call_openrouter_api(SVG_MODEL, svg_system_prompt, full_text)
        
        if svg_code:
            # 清理SVG内容，移除可能的markdown标记
            cleaned_svg = svg_code.strip()
            if cleaned_svg.startswith('```svg'):
                cleaned_svg = cleaned_svg[7:]  # 移除开头的```svg
            if cleaned_svg.endswith('```'):
                cleaned_svg = cleaned_svg[:-3]  # 移除结尾的```
            cleaned_svg = cleaned_svg.strip()
            
            # 修复SVG中的CSS问题，移除@import语句
            cleaned_svg = cleaned_svg.replace('@import url(\'https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap\');', '')
            cleaned_svg = cleaned_svg.replace('@import url("https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap");', '')
            
            # 替换字体引用为系统字体
            cleaned_svg = cleaned_svg.replace("'Noto Serif SC'", "'Arial', 'Helvetica', sans-serif")
            cleaned_svg = cleaned_svg.replace("'Noto Sans SC'", "'Arial', 'Helvetica', sans-serif")
            cleaned_svg = cleaned_svg.replace("'Space Mono'", "'Courier New', monospace")
            
            with open(os.path.join(record_dir, 'generated.svg'), 'w', encoding='utf-8') as f:
                f.write(cleaned_svg)
        else:
            logging.error(f"[ID: {tweet_id}] Failed to generate SVG content.")

        # --- Step 3: Save text files ---
        with open(body_file_path, 'w', encoding='utf-8') as f:
            f.write(body)
            
        logging.info(f"[ID: {tweet_id}] Successfully processed and saved to '{record_dir}'.")
        
        # --- Wait before next API call ---
        time.sleep(API_CALL_INTERVAL_SECONDS)

    logging.info("Processing complete.")

if __name__ == "__main__":
    main()

