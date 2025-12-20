import gradio as gr
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import ssl
import subprocess
import re
import shutil
import base64

# Global variable to store the path of the last successful run
LAST_RUN_HTML_PATH = None

runs_dir = "runs"
if os.path.exists(runs_dir) and os.path.isdir(runs_dir):
    latest_html_file = None
    latest_ctime = 0
    for subdir in os.listdir(runs_dir):
        full_subdir_path = os.path.join(runs_dir, subdir)
        if os.path.isdir(full_subdir_path):
            index_html_path = os.path.join(full_subdir_path, "index.html")
            if os.path.exists(index_html_path):
                ctime = os.path.getctime(index_html_path)
                if ctime > latest_ctime:
                    latest_ctime = ctime
                    latest_html_file = index_html_path
    LAST_RUN_HTML_PATH = latest_html_file

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


def generate_comic_html(idea, reuse_last_run=False, multi_page=False):
    """Call the agent to generate HTML and stream logs"""
    global LAST_RUN_HTML_PATH
    logs = []

    if reuse_last_run and LAST_RUN_HTML_PATH and os.path.exists(LAST_RUN_HTML_PATH):
        logs.append(f"♻️ Fast Mode: Reusing last run from {LAST_RUN_HTML_PATH}")
        print(logs[-1])
        try:
            with open(LAST_RUN_HTML_PATH, "r") as f:
                html_content = f.read()
            # Try to get graph from same run dir
            run_dir = os.path.dirname(LAST_RUN_HTML_PATH)
            graph_file = os.path.join(run_dir, "graph.png")
            graph_data_url = None
            if os.path.exists(graph_file):
                with open(graph_file, "rb") as f:
                    graph_data = f.read()
                graph_data_url = f"data:image/png;base64,{base64.b64encode(graph_data).decode('utf-8')}"
            yield html_content, "\n".join(logs), LAST_RUN_HTML_PATH, graph_data_url
            return
        except Exception as e:
            logs.append(f"❌ Error reading last run file: {e}")
            # Fall through to normal generation if reading fails

    logs.append(f"🎨 Starting comic generation for idea: {idea}")
    yield None, "\n".join(logs), None, None

    try:
        logs.append("🤖 Calling AI agent to create comic script...")
        print(logs[-1])
        yield None, "\n".join(logs), None, None

        if multi_page:
            cmd = ["python", "-u", "comicgen/main_story_gen.py", idea]
            if reuse_last_run:
                cmd.append("--fast")
            logs.append(f"📚 Multi-page mode enabled. Running: {' '.join(cmd)}")
        else:
            cmd = ["python", "-u", "comicgen/main.py", idea]
            if reuse_last_run:
                cmd.append("--fast")

        yield None, "\n".join(logs), None, None

        # Pipe output to file
        log_filename = "generation.log"
        with open(log_filename, "w") as f_out:
            process = subprocess.Popen(
                cmd, stdout=f_out, stderr=subprocess.STDOUT, cwd=".", text=True
            )

            # Read from file while running
            with open(log_filename, "r") as f_in:
                while process.poll() is None:
                    line = f_in.read()
                    if line:
                        logs.append(line)
                        yield None, "".join(logs), None, None
                    time.sleep(0.1)

                # Check for remaining output
                line = f_in.read()
                if line:
                    logs.append(line)
                    yield None, "".join(logs), None, None

        # Process finished
        if process.returncode == 0:
            full_log_text = "".join(logs)

            html_file = None
            all_lines = full_log_text.split("\n")
            for line in reversed(all_lines):
                # Regex for single page
                match = re.search(
                    r"Comic generated! Open (\./runs/[\w\-]+/index.html) to view.", line
                )
                if match:
                    html_file = match.group(1)
                    break
                # Regex for multi page
                match_story = re.search(
                    r"👉 Open this file to read: (\./runs/[\w\-]+/page_1.html)", line
                )
                if match_story:
                    html_file = match_story.group(1)
                    break

            if html_file is None:
                logs.append("\n❌ Could not find HTML file path in agent output.")
                yield None, "".join(logs), None, None
                return

            if os.path.exists(html_file):
                logs.append("\n📖 Comic HTML generated successfully!")
                LAST_RUN_HTML_PATH = html_file  # Update the last run path
                with open(html_file, "r") as f:
                    html_content = f.read()
                # Get graph PNG
                run_dir = os.path.dirname(html_file)
                graph_file = os.path.join(run_dir, "graph.png")
                graph_data_url = None
                if os.path.exists(graph_file):
                    with open(graph_file, "rb") as f:
                        graph_data = f.read()
                    graph_data_url = f"data:image/png;base64,{base64.b64encode(graph_data).decode('utf-8')}"
                    logs.append("\n📊 Graph visualization loaded!")
                yield html_content, "".join(logs), html_file, graph_data_url
            else:
                logs.append("\n❌ HTML file not found")
                yield None, "".join(logs), None, None
        else:
            logs.append(f"\n❌ Agent failed with return code {process.returncode}")
            yield None, "".join(logs), None, None
    except Exception as e:
        logs.append(f"\n❌ Error calling agent: {e}")
        yield None, "".join(logs), None, None


def send_email(to_email, html_content):
    """Send email with HTML attachment"""
    sender_email = os.environ.get("senderEmail")
    sender_password = os.environ.get("senderPassword")

    if not sender_password:
        print("Sender password not set.")
        return False

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = "Your Cartoon Comic!"

    body = "Here's your fun cartoon comic! 📚✨ Open the attached HTML file in your browser."
    msg.attach(MIMEText(body, "plain"))

    # Attach HTML as file
    part = MIMEBase("application", "octet-stream")
    part.set_payload(html_content.encode("utf-8"))
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment; filename=cartoon_comic.html")
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


def zip_run_folder(html_path):
    """Zip the folder containing the HTML file"""
    if not html_path or not os.path.exists(html_path):
        return None

    try:
        run_dir = os.path.dirname(html_path)
        # Verify it's a valid run directory (contains index.html)
        if not os.path.exists(os.path.join(run_dir, "index.html")):
            return None

        # Create zip file. make_archive adds the extension automatically.
        # We name the zip file the same as the run folder
        zip_base_name = run_dir

        print(f"Zipping folder: {run_dir} to {zip_base_name}.zip")
        archive_path = shutil.make_archive(zip_base_name, "zip", run_dir)
        return archive_path
    except Exception as e:
        print(f"Error zipping run folder: {e}")
        return None


def process_idea(idea, pdf_file, email, reuse_last_run, multi_page):
    print(
        f"Processing idea: {idea}, email: {email}, reuse_last_run: {reuse_last_run}, multi_page: {multi_page}"
    )
    if not email:
        yield "", "❌ Please enter your email!", gr.update(
            visible=False
        ), "<p style='text-align:center;'>🎭 Generate a comic to see it here!</p>", None
        return

    # Consume the generator
    final_html = None
    final_logs = ""
    final_file = None
    final_graph = None

    for html, logs_str, file_path, graph_url in generate_comic_html(
        idea, reuse_last_run, multi_page
    ):
        final_html = html
        final_logs = logs_str
        final_file = file_path
        final_graph = graph_url

        # Yield status update while running
        # We need to yield 5 outputs: output(status), logs(textarea), download buttons(update), iframe(html), graph(html)
        yield "Generating...", final_logs, gr.update(
            visible=False
        ), "<p style='text-align:center;'>⏳ Generating...</p>", None

    # Final processing
    zip_path = None
    if final_file:
        zip_path = zip_run_folder(final_file)

    if final_html:
        send_email(email, final_html)
        iframe_html = f"<iframe srcdoc='{final_html.replace(chr(39), '&#39;')}' width='100%' height='1000' style='border:1px solid #ccc;'></iframe>"
        graph_img = (
            f"<img src='{final_graph}' style='max-width:100%; height:auto;' />"
            if final_graph
            else ""
        )

        download_update = (
            gr.update(value=zip_path, visible=True, label="📥 Download Full Run (ZIP)")
            if zip_path
            else gr.update(
                value=final_file, visible=True, label="📥 Download HTML Only"
            )
        )

        yield "✅ Your cartoon comic has been sent to your email! 📧✨", final_logs, download_update, iframe_html, graph_img
    else:
        yield "❌ Failed to generate comic. Please try again.", final_logs, gr.update(
            visible=False
        ), "<p style='text-align:center;'>🎭 Generate a comic to see it here!</p>", ""


with gr.Blocks(title="🎨 Cartoon Generator for Learning anything!") as demo:
    gr.Markdown(
        "# 🎨 Cartoon Generator for Learning anything! 📚\nTurn your ideas into fun cartoon novels! 🌟"
    )

    example_html_display = gr.HTML(
        value="<p style='text-align:center;'>🎭 Generate a comic to see it here!</p>",
        label="Generated Comic",
    )

    with gr.Accordion("🎭 See Original Example Comic", open=False):
        try:
            with open("output.html", "r") as f:
                example_html = f.read()
            gr.HTML(
                f"<iframe srcdoc='{example_html.replace(chr(39), '&#39;')}' width='100%' height='1000' style='border:1px solid #ccc;'></iframe>"
            )
        except:
            gr.Markdown("Example comic not available yet. Generate one first!")

    email = gr.Textbox(
        label="📧 Your Email", placeholder="Enter your email to receive the comic"
    )
    idea = gr.TextArea(
        label="💡 Your Idea",
        placeholder="Describe your idea for a cartoon comic!",
        lines=5,
    )
    with gr.Row():
        reuse_last = gr.Checkbox(
            label="♻️ Reuse Last Run (Fast Mode)",
            value=False,
            info="Checking this skips generation if a run exists.",
        )
        multi_page = gr.Checkbox(
            label="📚 Multi-Page Story",
            value=False,
            info="Generate a longer multi-page story.",
        )

    pdf_file = gr.File(label="📄 Attach a PDF (optional)", file_types=[".pdf"])
    submit = gr.Button("🎨 Generate my Cartoon comic now!")
    progress = gr.HTML(visible=False)
    output = gr.Textbox(label="Status", interactive=False)
    logs = gr.TextArea(
        label="🎯 Processing Logs",
        interactive=False,
        lines=10,
        placeholder="Logs will appear here during processing...",
    )
    graph_display = gr.HTML(value="", label="Agent Graph Visualization")
    download = gr.DownloadButton("📥 Download Full Run (ZIP)", visible=False)

    submit.click(
        lambda: (
            gr.update(
                visible=True,
                value="""
    <div style='text-align:center; font-size:2em;'>
    ⏳ Creating your cartoon comic... <span class='spinner'>🔄</span><br>
    🎨 Drawing cartoons... 📖 Writing story... ✉️ Preparing email...
    </div>
    """,
            ),
            gr.update(interactive=False),  # disable button
            gr.update(
                value="<p style='text-align:center;'>⏳ Generating comic...</p>"
            ),  # update display
        ),
        outputs=[progress, submit, example_html_display],
    ).then(
        process_idea,
        [idea, pdf_file, email, reuse_last, multi_page],
        [output, logs, download, example_html_display, graph_display],
        show_progress=True,
    ).then(
        lambda: (
            gr.update(visible=False),
            gr.update(interactive=True),  # re-enable button
        ),
        outputs=[progress, submit],
    )


if __name__ == "__main__":
    demo.queue()
    demo.launch(
        server_name=os.getenv("SERVER_NAME", "127.0.0.1"),
        server_port=os.getenv("SERVER_PORT", 7660),
        share=os.getenv("SHARE", False),
        theme=gr.themes.Soft(),
        css=css,
        allowed_paths=["../runs", "."],
    )
