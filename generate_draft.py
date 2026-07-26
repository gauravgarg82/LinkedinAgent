#!/usr/bin/env python3
"""
Edgesoft LinkedIn Draft Agent
Generates one LinkedIn post draft per run, rotating through a topic bank,
and emails it for review. Designed to run 3x/week via GitHub Actions
(Mon = industry insight, Wed = leadership lesson, Fri = case study/personal take).
"""

import os
import sys
import json
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import anthropic

# ---------- Config ----------

MODEL = "claude-sonnet-5"

CONTENT_TYPE_BY_WEEKDAY = {
    0: "insight",     # Monday
    2: "leadership",  # Wednesday
    4: "case_study",  # Friday
}

CONTENT_TYPE_LABELS = {
    "insight": "Industry Insight",
    "leadership": "Engineering/Leadership Lesson",
    "case_study": "Case Study / Personal Take",
}

VOICE_INSTRUCTIONS = """
You are drafting a LinkedIn post for the CTO of Edgesoft, a gov-tech/permitting
software company whose clients are government agencies (permitting offices,
complaint management, data migration projects).

Voice: direct, technical-but-plain-English, no fluff, no hype-speak. Sounds like
an engineer who has actually built this stuff, not a marketer. No emojis in the
body. No "I'm thrilled to announce" energy. Short paragraphs (1-2 sentences each).
End with either a genuine question or a clear point of view, not a generic
call-to-action.

Hard constraints:
- Do NOT invent or reference specific client names, contract details, dollar
  figures, or anything that reads as confidential. Use generalized phrasing like
  "a city agency we've worked with" only if needed, and keep it vague.
- Do NOT oversell Edgesoft. Lead with the insight. Mention the company only if
  it's genuinely additive, and never as the headline.
- No corporate buzzwords: no "synergy," "leverage," "disrupt," "revolutionize."
- Keep it 100-200 words unless the topic genuinely needs more.
- Avoid partisan or political framing of "government" — stick to operational/
  technical framing (service delivery, system reliability, efficiency).

Output format:
1. A line "HOOK OPTION A:" followed by one possible opening line.
2. A line "HOOK OPTION B:" followed by an alternate opening line.
3. A line "DRAFT:" followed by the full post (you may reuse Hook A as the
   opening, or write a fresh opening — your call on what reads best).
"""

# ---------- Helpers ----------

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_content_type(override=None):
    if override:
        return override
    weekday = datetime.datetime.utcnow().weekday()
    return CONTENT_TYPE_BY_WEEKDAY.get(weekday, "insight")


def pick_topic(content_type, topics_path, state_path):
    topics = load_json(topics_path)
    state = load_json(state_path)

    bucket = topics[content_type]
    cursor = state.get(content_type, 0) % len(bucket)
    topic = bucket[cursor]

    state[content_type] = (cursor + 1) % len(bucket)
    save_json(state_path, state)

    return topic


def generate_draft(client, content_type, topic):
    label = CONTENT_TYPE_LABELS[content_type]

    user_prompt = f"""
Content type for today: {label}
Topic to write about: {topic}

Write the LinkedIn post now, following the voice and constraints above.
"""

    kwargs = {
        "model": MODEL,
        "max_tokens": 1000,
        "system": VOICE_INSTRUCTIONS,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    # For industry-insight posts, let Claude ground the take in something
    # current rather than writing purely from general knowledge.
    if content_type == "insight":
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
        kwargs["max_tokens"] = 1500

    response = client.messages.create(**kwargs)

    text_blocks = [b.text for b in response.content if b.type == "text"]
    return "\n\n".join(text_blocks).strip()


def build_email(content_type, topic, draft_text):
    label = CONTENT_TYPE_LABELS[content_type]
    today = datetime.date.today().strftime("%A, %B %d, %Y")
    subject = f"LinkedIn Draft — {label} — {today}"

    html = f"""
    <html>
    <body style="font-family: -apple-system, Arial, sans-serif; max-width: 640px; margin: 0 auto; color: #1a1a1a;">
      <h2 style="margin-bottom: 4px;">LinkedIn Draft: {label}</h2>
      <p style="color: #666; margin-top: 0;">{today}</p>
      <p style="color: #666; font-size: 13px;"><b>Topic seed:</b> {topic}</p>
      <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
      <div style="white-space: pre-wrap; line-height: 1.5; font-size: 15px;">{draft_text}</div>
      <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
      <p style="color: #999; font-size: 12px;">
        Before posting: double-check nothing here reads as client-confidential,
        and adjust the hook/tone to whatever feels right today. This is a first
        draft, not a final one.
      </p>
    </body>
    </html>
    """
    return subject, html


def send_email(subject, html_body):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", gmail_user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipient, msg.as_string())


# ---------- Main ----------

def main():
    override = sys.argv[1] if len(sys.argv) > 1 else None
    if override and override not in ("insight", "leadership", "case_study"):
        print(f"Unknown content type override: {override}")
        sys.exit(1)

    content_type = get_content_type(override)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    topics_path = os.path.join(base_dir, "config", "topics.json")
    state_path = os.path.join(base_dir, "state", "rotation_state.json")

    topic = pick_topic(content_type, topics_path, state_path)

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    draft_text = generate_draft(client, content_type, topic)

    subject, html_body = build_email(content_type, topic, draft_text)
    send_email(subject, html_body)

    print(f"Sent draft. Type: {content_type} | Topic: {topic}")


if __name__ == "__main__":
    main()
