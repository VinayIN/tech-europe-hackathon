# TechEU Editor

A comprehensive AI-powered text generation and modification system featuring multi-agent orchestration, web research capabilities, audio transcription, and cloud-based document storage.

## Installation

### Step 1: Clone & Navigate
```bash
git clone git@github.com:VinayIN/tech-europe-hackathon.git
cd tech-europe-hackathon
```

### Step 2: Environment Setup
Install using UV (recommended):
```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Step 3: Environment Configuration
Create a `.env` file in the project root:

```bash
# Core AI Services (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Web Scraping (Required for URL features)
ACI_API_KEY=your_aci_dev_api_key_here
LINKED_ACCOUNT_OWNER_ID=your_aci_account_owner_id

# Cloud Document Storage (Required)
WEAVIATE_URL=https://your-cluster.weaviate.network
WEAVIATE_API_KEY=your_weaviate_cloud_api_key

# Audio Transcription (Optional)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional Configuration
DEFAULT_LLM_MODEL=gpt-4o-mini
ELEVENLABS_MODEL_ID=eleven_monolingual_v1
MAX_SCRAPING_WORDS=150
REQUEST_TIMEOUT=30
```

### Step 4: Launch Application
```bash
python app.py
```

The application will start at `http://localhost:7860`

## Dependencies & Libraries

### Core Framework Dependencies
- **gradio (>=4.0.0)**: Modern web UI framework for machine learning applications
- **crewai[tools] (>=0.22.0)**: Multi-agent AI orchestration framework with built-in tools
- **openai (>=1.3.0)**: Official OpenAI API client for GPT models

### Specialized Service Libraries
- **elevenlabs (>=0.2.26)**: Audio transcription and speech-to-text processing
- **aci-sdk (>=0.1.0)**: ACI.dev integration for web scraping and BRAVE search
- **weaviate-client (>=4.8.0)**: Vector database client for semantic document storage


## AI Agents

### 1. Text Preparation Agent (`preparation_agent.py`)
**Purpose**: Research-based content generation with web integration

**Capabilities**:
- **Content Generation**: Creates 150-200 word articles using GPT-4o-mini
- **Web Research Integration**: Automatically incorporates URL content when provided
- **Citation Management**: Generates 2-5 structured citations with proper formatting
- **Multi-source Content**: Combines AI knowledge with web-scraped content

**Workflow**:
```
User Prompt + Optional URL → URL Scraping (if provided) → Content Generation → Citation Formatting → Output
```

### 2. Text Modification Agent (`modification_agent.py`)
**Purpose**: Context-Aware Generation (CAG) for text enhancement

**Architecture**:
- **Context Analyzer Agent**: Locates and analyzes text segments within larger documents
- **Text Modifier Agent**: Modifies identified sub-text while preserving context coherence

**Capabilities**:
- **Precise Text Location**: Identifies exact sub-text within source documents
- **Context Preservation**: Maintains document flow and surrounding content coherence
- **Word Count Control**: Keeps modifications within ±20% of original word count
- **Style Consistency**: Preserves tone and writing style

**CAG Workflow**:
```
Source Text + Sub-text Query + Modification Prompt → Context Analysis → Text Modification → Integrated Output
```

### 3. URL Scraping Agent (`url_scraping_agent.py`)
**Purpose**: Web content extraction and summarization

**Tools Integration**:
- **ACI.dev FIRECRAWL__EXTRACT**: Advanced web scraping with content filtering
- **Markdown Extraction**: Clean content extraction with ad blocking
- **Content Summarization**: Intelligent summarization to target word counts

## Project Structure

```
tech-europe-hackathon/
├── app.py                          # Main Gradio application entry point
├── pyproject.toml                  # Project configuration and dependencies
├── uv.lock                        # Dependency lock file
├── README.md                      # This documentation
├── .env                           # Environment variables (create this)
│
├── tech_europe_hackathon/                       # Main application package
│   ├── __init__.py               # Package initialization
│   │
│   ├── agents/                   # AI agent implementations
│   │   ├── __init__.py          # Agent package initialization
│   │   ├── preparation_agent.py # Research & content generation agent
│   │   ├── modification_agent.py # Context-aware text modification agent
│   │   └── url_scraping_agent.py # Web scraping and summarization agent
│   │
│   └── utils/                    # Core utility modules
│       ├── __init__.py          # Utils package initialization
│       ├── config.py            # Centralized configuration management
│       ├── document.py          # Weaviate cloud storage & document handling
│       └── audio.py             # ElevenLabs audio transcription
```

## User Interface Flow

### Preparation Mode Workflow

1. **Content Input Methods**:
   - **Text Prompt**: Direct text input for content generation
   - **Audio Upload**: Support for .wav, .mp3, .m4a, .flac, .ogg files
   - **Live Recording**: Real-time microphone input with transcription
   - **URL Integration**: Automatic web content incorporation

2. **Generation Process**:
   ```
   Input → AI Processing → Generated Content (150-200 words) → Citations → Source Panel
   ```

3. **Output Features**:
   - Live word/character/line counting
   - Structured footnotes with save/edit options
   - Automatic citation formatting

### Modification Mode Workflow

1. **Text Selection**:
   - Select text from Preparation panel
   - Copy to Context Area (read-only)
   - View selection indices and metadata

2. **Modification Process**:
   ```
   Context Text + Modification Prompt → CAG Processing → Modified Text → Modification Panel
   ```

3. **Integration**:
   - Apply modified text back to source
   - Precise replacement using tracked indices

### Document Management Flow

1. **Search & Discovery**:
   ```
   Search Query → Weaviate Vector Search → Matching Documents → Selection
   ```

2. **Loading Process**:
   ```
   Document Selection → Weaviate Retrieval → Content Loading → Preparation Panel
   ```

3. **Saving Workflow**:
   ```
   Content + Filename → Footnote Selection → Weaviate Storage → Confirmation
   ```

## Key Features

### Intelligent Content Generation
- **Multi-Agent Orchestration**: Specialized AI agents for different content creation tasks
- **Web-Enhanced Research**: Automatic integration of web content into generated articles
- **Citation Management**: Structured footnotes with proper formatting and URL tracking

### Advanced Document Management
- **Keyword Search**: Semantic similarity search using Weaviate cloud storage
- **Cloud Storage**: Persistent document storage with metadata and versioning
- **Smart Retrieval**: Search documents by content similarity, not just keywords

### Multimedia Input Support
- **Audio Transcription**: Support for multiple audio formats (.wav, .mp3, .m4a, .flac, .ogg)
- **Live Recording**: Real-time microphone input with instant transcription
- **Multimodal Interface**: Combined text and audio input processing

### Web Integration
- **URL Content Extraction**: Automatic web page content scraping and summarization

### User Experience
- **Real-time Feedback**: Live word counts, character counts, and selection tracking
- **Visual Mode Switching**: Intuitive panel-based workflow with visual feedback
- **Precise Text Handling**: Index-based text selection and replacement for accuracy

## API Keys & Configuration

1. **OpenAI Account**: 
   - Sign up at [platform.openai.com](https://platform.openai.com)
   - Generate API key from API section

2. **ACI.dev Account**:
   - Register at [aci.dev](https://aci.dev)
   - Get API key from dashboard
   - Note your Linked Account Owner ID

3. **Weaviate Cloud**:
   - Create cluster at [console.weaviate.cloud](https://console.weaviate.cloud)
   - Get cluster URL and API key

4. **ElevenLabs (Optional)**:
   - Sign up at [elevenlabs.io](https://elevenlabs.io)
   - Generate API key for speech-to-text features
