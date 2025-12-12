import gradio as gr
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import ssl
import subprocess

css = """
.gradio-container {
    background: linear-gradient(135deg, #ffeb3b, #ff9800, #e91e63, #9c27b0);
    background-size: 400% 400%;
    animation: gradientShift 10s ease infinite;
    font-family: 'Comic Sans MS', cursive, sans-serif;
}
@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.gr-button {
    background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
    border: none;
    border-radius: 50px;
    color: white;
    font-weight: bold;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    transition: all 0.3s ease;
}
.gr-button:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 20px rgba(0,0,0,0.3);
}
.gr-textbox, .gr-textarea, .gr-file {
    border-radius: 20px;
    border: 3px solid #ff6b6b;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
h1 {
    color: #ffffff;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    font-size: 2.5em;
    text-align: center;
}
.spinner {
    animation: spin 2s linear infinite;
}
@keyframes spin {
    0% {transform: rotate(0deg);}
    100% {transform: rotate(360deg);}
}
"""

def generate_comic_html(idea):
    """Call the agent to generate HTML"""
    logs = []
    logs.append(f"🎨 Starting comic generation for idea: {idea}")
    try:
        logs.append("🤖 Calling AI agent to create comic script...")
        result = subprocess.run(["python", "main.py", idea], cwd=".", capture_output=True, text=True)
        logs.extend(result.stdout.split('\n'))
        logs.extend(result.stderr.split('\n'))
        if result.returncode == 0:
            html_file = "output.html"
            if os.path.exists(html_file):
                logs.append("📖 Comic HTML generated successfully!")
                with open(html_file, "r") as f:
                    html_content = f.read()
                return html_content, '\n'.join(logs)
            else:
                logs.append("❌ HTML file not found")
        else:
            logs.append(f"❌ Agent failed with return code {result.returncode}")
    except Exception as e:
        logs.append(f"❌ Error calling agent: {e}")
    return None, '\n'.join(logs)

def send_email(to_email, html_content):
    """Send email with HTML attachment"""
    sender_email = os.environ.get('senderEmail')
    sender_password = os.environ.get('senderPassword')

    if not sender_password:
        print("Sender password not set.")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = "Your Cartoon Comic!"

    body = "Here's your fun cartoon comic! 📚✨ Open the attached HTML file in your browser."
    msg.attach(MIMEText(body, 'plain'))

    # Attach HTML as file
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(html_content.encode('utf-8'))
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename=cartoon_comic.html")
    msg.attach(part)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        print(f"Cartoon comic sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send comic to {to_email}: {e}")
        return False

def process_idea(idea, pdf_file, email):
    print(f"Processing idea: {idea}, email: {email}")
    if not email:
        return "", "❌ Please enter your email!", gr.update(visible=False)
    html_content, logs = generate_comic_html(idea)
    print("HTML content generated:", html_content is not None)
    print("Logs:", logs)
    if html_content:
        send_email(email, html_content)
        return "✅ Your cartoon comic has been sent to your email! 📧✨", logs, gr.update(value="output.html", visible=True)
    else:
        return "❌ Failed to generate comic. Please try again.", logs, gr.update(visible=False)

with gr.Blocks(title="🎨 Cartoon Generator for Learning anything!") as demo:
    gr.Markdown("# 🎨 Cartoon Generator for Learning anything! 📚\nTurn your ideas into fun cartoon novels! 🌟")

    with gr.Accordion("🎭 See Example Comic", open=False):
        try:
            with open("output.html", "r") as f:
                example_html = f.read()
            gr.HTML(f"<iframe srcdoc='{example_html.replace(chr(39), '&#39;')}' width='100%' height='600' style='border:1px solid #ccc;'></iframe>")
        except:
            gr.Markdown("Example comic not available yet. Generate one first!")

    email = gr.Textbox(label="📧 Your Email", placeholder="Enter your email to receive the comic")
    idea = gr.TextArea(label="💡 Your Idea", placeholder="Describe your idea for a cartoon comic!", lines=5)
    pdf_file = gr.File(label="📄 Attach a PDF (optional)", file_types=[".pdf"])
    submit = gr.Button("🎨 Generate my Cartoon comic now!")
    progress = gr.HTML(visible=False)
    output = gr.Textbox(label="Status", interactive=False)
    logs = gr.TextArea(label="🎯 Processing Logs", interactive=False, lines=10, placeholder="Logs will appear here during processing...")
    download = gr.DownloadButton("📥 Download Comic HTML", visible=False)

    submit.click(
        lambda: gr.update(visible=True, value="<div style='text-align:center; font-size:2em;'>⏳ Creating your cartoon comic... <span class='spinner'>🔄</span><br>🎨 Drawing cartoons... 📖 Writing story... ✉️ Preparing email...</div>"),
        None,
        progress
    ).then(
        process_idea,
        [idea, pdf_file, email],
        [output, logs, download]
    ).then(
        lambda: gr.update(visible=False),
        None,
        progress
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7660, share=True, theme=gr.themes.Soft(), css=css)
