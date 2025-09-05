# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Twitter/X tweet processing tool that transforms tweet content into two formats:
1. **SVG images** - High-end magazine-style knowledge cards using 29 different design styles
2. **Xiaohongshu (Little Red Book) copy** - Social media content optimized for Chinese platforms

The tool processes tweets from a sorted JSON dataset and generates organized output files for each record.

## Key Architecture Changes

**Multi-Provider API Architecture**:
- **Primary Providers**: OpenRouter, SiliconFlow, Novita.ai, Moonshot, Gemini
- **Task-Specific Models**: Different models for title, body, and SVG generation
- **Fallback Mechanism**: Automatic failover to alternative providers
- **Rate Limiting**: Provider-specific rate limiting with auto-handling

## Core Architecture

### Main Components

- **`process_tweets.py`** - Simple processor with basic functionality
- **`batch_process_tweets.py`** - Advanced processor with class-based architecture, CLI arguments, and enhanced error handling
- **`TweetProcessor` class** - Main processing logic with multi-provider API support and progress tracking
- **`api_client.py`** - Unified API client module with provider abstraction and fallback mechanisms
- **Configuration Files** - `config.json` and `.env` support for flexible multi-provider configuration

### Key Dependencies
- `openai>=1.0.0` - Unified API client for multiple providers
- `tqdm>=4.65.0` - Progress bars for batch processing
- `python-dotenv>=1.0.0` - Environment variable management
- `pathlib` - Modern path handling (built-in)

### Multi-Provider Configuration

The system supports 5 API providers with task-specific model assignment:

**Task-to-Provider Mapping**:
- **Title Generation**: SiliconFlow (DeepSeek-V3.1) → Moonshot (kimi-k2-0711-preview)
- **Body Generation**: Novita.ai (DeepSeek-V3.1) → Moonshot (kimi-k2-0711-preview)  
- **SVG Generation**: Novita.ai (DeepSeek-V3.1) → SiliconFlow (DeepSeek-V3.1) → OpenRouter (DeepSeek-Chat) → Moonshot (kimi-k2-0711-preview)

**Provider Endpoints**:
- OpenRouter: `https://openrouter.ai/api/v1`
- SiliconFlow: `https://api.siliconflow.cn/v1`
- Novita.ai: `https://api.novita.ai/openai`
- Moonshot: `https://api.moonshot.cn/v1`
- Gemini: `http://xai-studio.top:8000/openai/v1`

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Environment Configuration
```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env file with your API keys for all providers
```

### Running the Processor
```bash
# Basic usage (first 5 records)
python batch_process_tweets.py --count 5

# Process all records with default configuration
python batch_process_tweets.py

# Process specific range
python batch_process_tweets.py --start 10 --count 20

# Custom file paths
python batch_process_tweets.py \
    --input "custom_data.json" \
    --svg-prompt "custom_svg_prompt.txt" \
    --xiaohongshu-prompt "custom_xhs_prompt.txt"

# Using specific config file
python batch_process_tweets.py --config "custom_config.json"
```

### Simple Example
```bash
# Ensure all API keys are set in .env file
python run_example.py
```

### Testing Individual Components
```bash
# Test API connectivity
python -c "from api_client import create_client; print('API client test')"

# Validate configuration
python -c "import json; print(json.load(open('config.json')))"
```

## File Structure Requirements

The project expects these files in the working directory:
- `twillot-public-post-sorted.json` - Tweet dataset (1667 records)
- `svg提示词.txt` - SVG generation system prompt (29 design styles)
- `小红书文案提示词.txt` - Xiaohongshu copywriting system prompt
- `小红书标题提示词.txt` - Title generation system prompt
- `config.json` - Multi-provider configuration file
- `.env` - Environment variables for API keys

### Required Environment Variables
- `OPENROUTER_API_KEY` - OpenRouter API key
- `SILICONFLOW_API_KEY` - SiliconFlow API key
- `NOVITA_API_KEY` - Novita.ai API key
- `MOONSHOT_API_KEY` - Moonshot API key
- `GEMINI_API_KEY` - Gemini API key

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

Multi-provider API configuration with automatic failover:

### Provider-Specific Configuration
- **OpenRouter**: 4-second intervals, 16 requests/minute limit
- **SiliconFlow**: 2-second intervals, DeepSeek-V3.1 model
- **Novita.ai**: 2-second intervals, DeepSeek-V3.1 model
- **Moonshot**: 2-second intervals, kimi-k2-0711-preview model
- **Gemini**: 2-second intervals, custom endpoint

### Rate Limiting & Retry Logic
- **Provider-specific intervals**: Configurable per provider
- **Automatic fallback**: Failover to next provider on failure
- **Retry attempts**: 3 attempts per provider
- **429 error handling**: Special retry logic with exponential backoff
- **Smart waiting**: Monitors rate limit headers automatically

### Environment Variables
- `OPENROUTER_API_KEY`: OpenRouter API key
- `SILICONFLOW_API_KEY`: SiliconFlow API key
- `NOVITA_API_KEY`: Novita.ai API key
- `MOONSHOT_API_KEY`: Moonshot API key
- `GEMINI_API_KEY`: Gemini API key
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

### Multi-Provider Fallback System
- **Task-specific routing**: Different providers for title, body, and SVG generation
- **Automatic failover**: Seamless switching to backup providers on failure
- **Provider health monitoring**: Tracks success rates and response times
- **Circuit breaker pattern**: Temporarily disables failing providers

### Rate Limiting Handling
- **Provider-specific detection**: Monitors x-ratelimit headers per provider
- **Smart waiting**: Dynamic wait times based on remaining quota
- **429 error handling**: Exponential backoff with provider-specific intervals
- **Header parsing**: Automatic extraction of rate limit information

### SVG Processing Pipeline
- **Markdown cleanup**: Removes ```svg code block markers
- **Font processing**: Strips @import statements, replaces with system fonts
- **Compatibility optimization**: Ensures cross-browser SVG compatibility
- **Chinese text enhancement**: Improved handling of Chinese characters and typography

### Content Generation Pipeline
- **Separate title generation**: Dedicated provider for optimal title creation
- **Body content optimization**: Provider-specific handling for body content
- **Content filtering**: Removes section headers and formatting artifacts
- **Emoji/hashtag preservation**: Maintains social media formatting elements

### File Management System
- **Conflict resolution**: Automatic numeric suffixes for duplicate filenames
- **Progress tracking**: JSON-based progress state persistence
- **Resume capability**: Skips already processed records
- **Organized structure**: Hierarchical output directory organization

### Configuration Management
- **JSON-based configuration**: Centralized provider and task configuration
- **Environment variable override**: Flexible configuration via environment variables
- **Validation**: Automatic validation of configuration structure
- **Hot reload**: Configuration changes without code modification

## Security Notes

- API keys should be set via environment variables (one per provider)
- No hard-coded API keys in production code
- Configuration files should not be committed to version control
- No sensitive data is logged or stored in output files
- All file operations use UTF-8 encoding for Chinese content
- Provider credentials are isolated and access-controlled

## Architecture Evolution

### Migration from Single-Provider to Multi-Provider
1. **API Abstraction**: Introduced `BaseAPIClient` class for provider abstraction
2. **Configuration Centralization**: Moved to JSON-based provider configuration
3. **Task-Specific Routing**: Different providers optimized for different content types
4. **Enhanced Error Handling**: Multi-level fallback and retry mechanisms
5. **Provider Health Monitoring**: Success rate tracking and automatic failover

### Benefits of Multi-Provider Architecture
- **Reliability**: No single point of failure
- **Cost Optimization**: Use best-priced provider for each task
- **Performance**: Provider-specific optimization for different content types
- **Scalability**: Easy to add new providers without code changes
- **Resilience**: Automatic failover ensures continuous operation