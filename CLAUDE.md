# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Twitter/X tweet processing tool that transforms tweet content into two formats:
1. **SVG images** - High-end magazine-style knowledge cards using 29 different design styles
2. **Xiaohongshu (Little Red Book) copy** - Social media content optimized for Chinese platforms

The tool processes tweets from a sorted JSON dataset and generates organized output files for each record.

## Key Changes

**Migrated from Poe API to OpenRouter API**:
- **New API Base**: `https://openrouter.ai/api/v1`
- **New Model**: `moonshotai/kimi-k2:free`
- **Environment Variable**: `OPENROUTER_API_KEY`
- **Rate Limiting**: 16 requests per minute (auto-handled)

## Core Architecture

### Main Components

- **`process_tweets.py`** - Simple processor with basic functionality
- **`batch_process_tweets.py`** - Advanced processor with class-based architecture, CLI arguments, and enhanced error handling
- **`TweetProcessor` class** - Main processing logic with retry mechanisms and progress tracking
- **API Integration** - Uses OpenRouter API with deepseek/deepseek-chat-v3-1:free model for both SVG and content generation
- **Configuration Files** - `config.json` and `.env` support for flexible configuration

### Key Dependencies
- `openai>=1.0.0` - API client for OpenRouter integration
- `tqdm>=4.65.0` - Progress bars for batch processing
- `pathlib` - Modern path handling (built-in)

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Running the Processor
```bash
# Basic usage (first 5 records)
python batch_process_tweets.py --api-key "your_openrouter_api_key_here" --count 5

# Process all records
python batch_process_tweets.py --api-key "your_openrouter_api_key_here"

# Process specific range
python batch_process_tweets.py --api-key "your_openrouter_api_key_here" --start 10 --count 20

# Using environment variable (recommended)
export OPENROUTER_API_KEY="your_api_key_here"
python batch_process_tweets.py --count 5

# Custom file paths
python batch_process_tweets.py \
    --api-key "your_openrouter_api_key_here" \
    --input "custom_data.json" \
    --svg-prompt "custom_svg_prompt.txt" \
    --xiaohongshu-prompt "custom_xhs_prompt.txt"
```

### Simple Example
```bash
# Set environment variable first
export OPENROUTER_API_KEY="your_api_key_here"
python run_example.py
```

## File Structure Requirements

The project expects these files in the working directory:
- `twillot-public-post-sorted.json` - Tweet dataset (1667 records)
- `svg提示词.txt` - SVG generation system prompt (29 design styles)
- `小红书文案提示词.txt` - Xiaohongshu copywriting system prompt

## Output Organization

Generated files are organized in `output/` directory:
```
output/
├── 标题1/
│   ├── generated.svg    # Magazine-style SVG card
│   ├── title.txt       # Extracted title
│   └── body.txt        # Content with hashtags
├── 标题2/
│   ├── generated.svg
│   ├── title.txt
│   └── body.txt
```

## API Configuration

Uses OpenRouter API (https://openrouter.ai/keys) with:
- **Base URL**: `https://openrouter.ai/api/v1`
- **Model**: `deepseek/deepseek-chat-v3-1:free` for both SVG and content generation
- **Rate limiting**: 4-second intervals between calls (auto-handled)
- **Retry mechanism**: 3 attempts with special handling for 429 errors
- **Headers**: Includes HTTP-Referer and X-Title headers

### Environment Variables
- `OPENROUTER_API_KEY`: Your OpenRouter API key (required)
- `CONFIG_FILE`: Optional path to config file
- `LOG_LEVEL`: Optional logging level

## Key Features

### Processing Capabilities
- **Resume functionality**: Skips already processed records
- **Error handling**: Comprehensive logging to `batch_process.log`
- **Progress tracking**: Real-time progress bars with tqdm
- **File conflict resolution**: Automatic numeric suffixes for duplicates

### Content Generation
- **SVG Design**: 29 magazine-style templates (minimalist, luxury, tech, etc.)
- **Content parsing**: Extracts titles and body from API responses
- **File sanitization**: Handles invalid filename characters
- **Font fallback**: Replaces Google Fonts with system fonts for compatibility

## Error Handling & Logging

- **Dual logging**: Console output + file logging (`batch_process.log`)
- **API retries**: 3 attempts with 5-second delays
- **File validation**: Checks for required files on startup
- **Graceful degradation**: Continues processing after individual failures

## Important Implementation Details

### Rate Limiting Handling
- **Automatic detection**: Monitors x-ratelimit-remaining and x-ratelimit-reset headers
- **Smart waiting**: Waits appropriate time when approaching limits
- **429 error handling**: Special retry logic for rate limit errors
- **Configurable intervals**: 4-second base interval with buffer time

### SVG Processing
- Removes markdown code block markers (```svg)
- Strips @import statements for external fonts
- Replaces custom fonts with system fallbacks
- Ensures SVG compatibility across browsers
- Enhanced Chinese text detection and processing

### Content Parsing
- Handles Chinese text encoding (UTF-8)
- Extracts titles from first line of API response
- Filters out section headers ("2. 正文", "Body:", etc.)
- Preserves emoji and hashtag formatting
- DeepSeek model optimized for Chinese content

### File Management
- Automatic directory creation with conflict resolution
- Filename sanitization (100-character limit)
- Skip logic for existing completed records
- Organized output structure for easy browsing

### Configuration Management
- **config.json**: Main configuration file with API settings
- **.env**: Environment variable support
- **config.example.json**: Template for configuration
- **Fallback logic**: Environment variables override config files

## Security Notes

- API keys should be set via environment variable `OPENROUTER_API_KEY`
- No hard-coded API keys in production code
- Configuration files should not be committed to version control
- No sensitive data is logged or stored in output files
- All file operations use UTF-8 encoding for Chinese content

## Migration from Poe API

### Key Changes
1. **API Endpoint**: Changed from Poe to OpenRouter
2. **Model**: Switched from Claude-Sonnet-4 to deepseek/deepseek-chat-v3-1:free
3. **Rate Limiting**: Enhanced handling for OpenRouter's 16 req/min limit
4. **Headers**: Added OpenRouter-specific HTTP headers
5. **Error Handling**: Improved 429 error handling

### Benefits
- **Cost**: DeepSeek model is currently free
- **Chinese Support**: Better Chinese language processing
- **Rate Limiting**: More predictable rate limits with auto-handling