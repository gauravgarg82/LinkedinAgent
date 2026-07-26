# Edgesoft LinkedIn Draft Agent

Emails you one ready-to-review LinkedIn post draft, 3x/week (Mon/Wed/Fri, ~7:00 AM IST),
rotating through a topic bank so it doesn't repeat itself for months. Same setup pattern
as your other agents: Python + GitHub Actions + Claude API + Gmail SMTP.

## What it sends

- **Monday** — industry insight (uses web search to ground it in something current)
- **Wednesday** — engineering/leadership lesson
- **Friday** — case study / personal take (always generalized, never client-identifying)

Each email has the topic seed, a full draft, two alternate hook/opening lines, and a
reminder to sanity-check for confidentiality before posting. You copy-paste into
LinkedIn yourself — nothing auto-publishes.

## Setup

### 1. Create the repo
Push this folder to a new GitHub repo (private is fine — recommended, since the
topic list and prompt live here).

```bash
cd edgesoft-linkedin-agent
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

### 2. Get a Gmail App Password
(Same steps as your other email agents.)
1. Go to your Google Account → Security → 2-Step Verification (must be on).
2. Go to Security → App passwords.
3. Generate one for "Mail" / "Other (custom name)" → name it `linkedin-draft-agent`.
4. Copy the 16-character password.

### 3. Add GitHub repo secrets
Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic Console API key |
| `GMAIL_USER` | The Gmail address sending the emails |
| `GMAIL_APP_PASSWORD` | The 16-character app password from step 2 |
| `RECIPIENT_EMAIL` | Where drafts should land (can be same as `GMAIL_USER`) |

### 4. Test it manually
Go to the repo's **Actions** tab → "LinkedIn Draft Generator" → **Run workflow**.
You can optionally type `insight`, `leadership`, or `case_study` in the input box
to force a specific type instead of waiting for the scheduled day.

If it runs clean, you'll get an email within a minute or two.

### 5. Let it run
Once secrets are set, the schedule in `.github/workflows/linkedin-drafts.yml` handles
the rest — no further action needed. GitHub Actions cron jobs can occasionally fire a
few minutes late; that's normal.

## Customizing

- **Change the schedule/days:** edit the `cron` line in the workflow file. Cron is in
  UTC — 7:00 AM IST is `1:30 UTC`, so adjust the hour if you want a different local time.
- **Add/edit topics:** edit `config/topics.json`. Each content type (`insight`,
  `leadership`, `case_study`) is a list — add as many as you want, they rotate in order
  and loop back around.
- **Change the voice/constraints:** edit `VOICE_INSTRUCTIONS` in `generate_draft.py` —
  this is the same voice/guardrails from the LinkedIn playbook (no client names, no
  overselling Edgesoft, no buzzwords, etc.).
- **Reset rotation:** edit `state/rotation_state.json` back to all `0`s if you want to
  restart the topic cycle from the top.

## Notes

- The rotation state (`state/rotation_state.json`) is committed back to the repo after
  every run, so topics won't repeat until the whole bucket has cycled through.
- If you ever want this to *also* draft from something specific that week (a client
  win, an article, a meeting note) rather than the rotating topic bank, just use the
  prompt template from the LinkedIn playbook directly in a Claude conversation — this
  agent is for the "keep something flowing even in a busy week" baseline, not a
  replacement for posting about something timely when it happens.
