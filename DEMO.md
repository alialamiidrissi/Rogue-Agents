# Demo Video

The Cartoon Generator demo showcases how AI agents create educational comics through multi-step orchestration using Google Gemini.

## Demo Overview

This demo illustrates the complete workflow of generating a custom educational cartoon comic about any topic, demonstrating the agent's planning, tool integration, and creative output capabilities.

## Key Demo Elements

- **Problem Solved**: Making complex educational topics accessible and engaging through visual storytelling
- **Agent Behavior**: End-to-end comic generation from user input to email delivery
- **Agentic Steps**: Structured planning, creative asset generation, and automated composition

---

📺 **Demo Video Link:**
[To be added - Create a 3-5 minute video showing the app in action]

### Proposed Timestamps

- **00:00–00:30** — Introduction & Educational Problem
  - Show the app interface and explain the concept
  - Demonstrate the kid-friendly UI with example comic preview
  - Highlight the educational impact goal

- **00:30–01:30** — User Input & Planning Phase
  - Enter email and describe a topic (e.g., "Newton explaining gravity")
  - Show real-time console logging as Director Node analyzes input
  - Display the structured JSON comic script generation
  - Explain how LangGraph orchestrates the workflow

- **01:30–02:30** — Tool Calls & Creative Generation
  - Demonstrate Asset Generator Node creating SVG characters
  - Show Gemini API calls for character design and HTML composition
  - Display progress logs updating in real-time
  - Highlight the creative AI capabilities

- **02:30–03:30** — Final Output & Delivery
  - Show completed HTML comic rendering
  - Demonstrate email delivery with attachment
  - Display download functionality
  - Discuss scalability and real-world applications

- **03:30–04:00** — Edge Cases & Error Handling
  - Test with invalid inputs and missing API keys
  - Show error recovery and user feedback
  - Demonstrate PDF integration for additional context

## Demo Script

**Narrator:** "Welcome to Cartoon Generator for Learning Anything! This innovative app uses AI agents to transform any educational topic into engaging cartoon comics.

Watch as I create a comic about Newton's law of gravity. The system uses a sophisticated LangGraph agent that breaks down the task into three specialized nodes: Director for planning, Asset Generator for characters, and Compositor for final assembly.

As you can see, the console shows real-time progress - first the Director analyzes the input and creates a structured script, then the Asset Generator crafts unique SVG characters, and finally the Compositor assembles everything into a beautiful HTML comic.

The result is emailed directly to the user and available for download. This makes learning fun and accessible for students of all ages!"

## Demo Requirements

- Record screen capture of the Gradio interface
- Show console logs during generation
- Include email inbox showing received comic
- Demonstrate multiple topics (science, history, math)
- Highlight the agentic decision-making process
- Show error handling with invalid inputs

Videos longer than 5 minutes may not be fully reviewed.
