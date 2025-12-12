# Technical Explanation

## 1. Agent Workflow

The Cartoon Generator agent follows a structured 3-stage pipeline using LangGraph for orchestration:

1. **User Input Reception**: Gradio UI collects email, idea description, and optional PDF
2. **Director Node**: Analyzes user prompt and generates structured JSON comic script with 3 panels, characters, dialogue, and backgrounds
3. **Asset Generator Node**: Creates unique SVG characters for each character in the script using Gemini's creative generation
4. **Compositor Node**: Assembles final HTML with positioned characters, speech bubbles, and backgrounds
5. **Email Delivery**: Sends completed HTML comic as attachment via Gmail SMTP
6. **UI Update**: Displays logs, status, and download link to user

## 2. Key Modules

- **main.py**: Core agent implementation with LangGraph workflow
  - director_node(): Script planning and JSON generation
  - asset_generator_node(): SVG character creation
  - compositor_node(): HTML composition and styling
- **gradio_chatbot.py**: Web interface and subprocess orchestration
  - process_idea(): Main processing function
  - generate_comic_html(): Agent subprocess execution
  - send_email(): Email delivery system
- **requirements.txt**: All Python dependencies
- **.env**: Environment variables for API keys

## 3. Tool Integration

The system integrates several tools and APIs:

- **Google Gemini 2.5 Flash**: Primary LLM via langchain-google-genai
  - Used for script generation with structured JSON output mode
  - Creative SVG generation for characters
  - HTML composition with CSS styling
  - Called via ChatGoogleGenerativeAI.invoke() with temperature settings

- **Gmail SMTP**: Email delivery system
  - Uses smtplib.SMTP_SSL for secure connection
  - Attaches HTML files as MIMEBase
  - Requires app password for authentication

- **PyPDF**: PDF text extraction
  - Extracts text from uploaded PDF files
  - Integrates additional context into comic generation

- **ReportLab**: Backup PDF generation (not currently used)

## 4. Observability & Testing

Logging and observability features:

- **Console Logging**: Real-time progress with emojis and sys.stdout.flush()
  - Tracks each node execution start/completion
  - Shows character asset generation
  - Reports email sending status
  - Displays in terminal where Gradio runs

- **UI Logging**: Subprocess stdout/stderr captured and displayed in Gradio textarea
  - Shows complete agent execution logs
  - Includes Gemini API responses and errors
  - Updates after processing completion

- **Error Handling**: Comprehensive try/catch blocks
  - Agent subprocess failures
  - API key validation
  - Email sending errors
  - File I/O operations

- **Progress Indicators**: Visual feedback during generation
  - Animated spinner with status messages
  - Real-time UI updates

Testing can be done by running `python main.py "test topic"` directly or through the Gradio interface.

## 5. Known Limitations

Current system limitations and edge cases:

- **API Dependency**: Requires valid Google Gemini API key and credits
- **Generation Time**: 30-60 seconds per comic due to multiple LLM calls
- **Character Limits**: Max 2 characters per panel, 3 panels total
- **Memory Scope**: No persistent memory - each generation is independent
- **Email Reliability**: Depends on Gmail SMTP availability and app password setup
- **Content Filtering**: No explicit content moderation for user inputs
- **Browser Compatibility**: HTML comics optimized for modern browsers
- **File Size**: Large PDFs may cause processing delays
- **Error Recovery**: Limited retry logic for failed API calls
- **Scalability**: Single-threaded processing, not optimized for concurrent users
