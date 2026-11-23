import sys
from pathlib import Path

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from sqlmodel import Session, select
from app.db import engine, init_db
from app.models import Incident


def seed():
    docs_dir = BASE_DIR / "data" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    init_db()

    # 1. Corporate VPN Troubleshooting Guide
    (docs_dir / "vpn.md").write_text(
        """# Corporate VPN Troubleshooting Guide

The enterprise uses GlobalProtect and WireGuard for secure remote network access.

## Symptoms & Resolutions
1. **VPN Status Connected but Internal Services Unreachable:**
   - Confirm you are connected to the primary gateway (`vpn.corp.company.com`).
   - Check if your route table includes the `10.0.0.0/8` corporate subnets:
     - On macOS/Linux: `netstat -nr | grep 10.`
     - On Windows: `route print 10.*`
   - If routes are missing, disconnect, toggle Wi-Fi, and reconnect.
2. **Split Tunneling Behavior:**
   - Public internet traffic (e.g. YouTube, public web) goes directly through your ISP.
   - Internal domains (*.corp.internal, gitlab.corp, jira.corp) route through the encrypted tunnel.
3. **DNS Resolution Failure:**
   - Flush local DNS cache:
     - Windows: `ipconfig /flushdns`
     - macOS: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
4. **Certificate Validation Errors:**
   - Open Jamf / InTune Company Portal and check for the "Corp-Root-CA-2026" profile. Reinstall if missing.
5. **Escalation:**
   - If the issue persists, open an IT ticket with your OS version, IP address, and route table output.
""",
        encoding="utf-8",
    )

    # 2. Internal GitLab Guide
    (docs_dir / "gitlab.md").write_text(
        """# Internal GitLab & Code Repository Access Guide

GitLab (`gitlab.corp.internal`) hosts all proprietary source code and CI/CD pipelines.

## Prerequisites
- Active corporate VPN connection required if working remotely.
- Hardware security key or Okta Verify MFA registered.

## Common Issues & Troubleshooting
1. **SSH Connection Refused or Timeout (`git@gitlab.corp.internal`):**
   - Verify VPN connection is active.
   - Test connectivity: `ssh -Tv git@gitlab.corp.internal -p 22`
   - Ensure your SSH public key (`~/.ssh/id_ed25519.pub`) is added in GitLab Profile -> Settings -> SSH Keys.
2. **GitLab CI Runner Unreachable:**
   - Shared runners are isolated in VPC `subnet-ci-runners-01`.
   - Contact DevOps on #ask-devops or file an IT ticket if jobs queue for >10 minutes.
3. **2FA / Backup Codes:**
   - If you lost your 2FA device, an IT administrator must temporarily generate one-time recovery codes via Okta Directory Sync.
""",
        encoding="utf-8",
    )

    # 3. Wi-Fi and Corporate Network Access
    (docs_dir / "wifi_network.md").write_text(
        """# Office Wi-Fi & Wired Network Access

The enterprise maintains three wireless networks:
- **Corp-Secure:** For managed laptops only. Uses 802.1X EAP-TLS certificate authentication.
- **Corp-Guest:** For visitors and contractor personal devices. Requires captive portal phone validation.
- **IoT-Hardware:** Dedicated for test benches and smart displays (MAC address whitelisted).

## Troubleshooting "Corp-Secure" Connection Failures
1. Forget the network "Corp-Secure" in your operating system Wi-Fi settings.
2. Reconnect and select certificate authentication (select your user certificate issued by Corp-CA).
3. If no certificate is found, run the InTune/Jamf Self-Service app and run "Renew Wi-Fi Certificates".
4. Ensure your machine's clock is synchronized with NTP (`time.windows.com` or `time.apple.com`).
""",
        encoding="utf-8",
    )

    # 4. Okta SSO & MFA Guide
    (docs_dir / "sso_okta.md").write_text(
        """# Single Sign-On (Okta) & Multi-Factor Authentication

All corporate applications (Google Workspace, Slack, Jira, AWS, Workday) authenticate through Okta SSO.

## Common Issues
1. **MFA Push Notification Loop / Not Receiving Push:**
   - Open Okta Verify on your smartphone and pull down to refresh notifications.
   - Ensure "Do Not Disturb" or "Focus Mode" is not silencing Okta Verify.
   - If you changed your mobile device, submit an IT ticket for an MFA factor reset.
2. **Account Locked Out:**
   - 5 consecutive incorrect password attempts will lock the account for 15 minutes.
   - Use the self-service "Unlock Account" link via SMS verification, or contact the IT Helpdesk.
3. **Session Timeout Policy:**
   - Standard session lifetime is 12 hours. High-security apps (AWS Console, Production DBs) timeout after 60 minutes of inactivity.
""",
        encoding="utf-8",
    )

    # 5. Laptop Hardware & OS Provisioning
    (docs_dir / "hardware_laptop.md").write_text(
        """# Laptop Hardware, BitLocker & FileVault Recovery

Corporate laptops are enrolled in MDM management for security and compliance.

## Drive Encryption & Recovery Keys
1. **Windows BitLocker Recovery Prompt:**
   - Usually triggered by firmware/BIOS updates or dock changes.
   - BitLocker recovery keys can be retrieved self-service via `https://portal.manage.microsoft.com` under My Devices -> Recovery Keys.
   - Alternatively, IT Helpdesk can read the key from Azure Active Directory.
2. **macOS FileVault:**
   - Escrowed institutional recovery keys are held in Jamf Pro.
3. **External Displays & Thunderbolt Docks:**
   - If external monitors do not wake up, disconnect dock power for 10 seconds (power cycle).
   - Update DisplayLink drivers if using DisplayLink dual-display adapters.
""",
        encoding="utf-8",
    )

    # 6. Software Requests & Licensing
    (docs_dir / "software_requests.md").write_text(
        """# Software Catalog & License Procurement

Standard pre-approved software is distributed through Self Service (macOS) and Company Portal (Windows).

## Pre-approved Software (Zero Approval Required):
- Google Chrome, Firefox Developer Edition
- VS Code, PyCharm Community, Sublime Text
- Slack, Zoom, 1Password, Notion

## Commercial Licenses Requiring Manager Approval:
- **Docker Desktop Commercial License:** File a software request ticket citing business justification.
- **JetBrains All Products Pack:** Available for Full-Time Software Engineers.
- **Figma Organization Editor Seat:** Granted to Product, Design, and Front-End Engineers.
- **AWS IAM Administrator Access:** Requires Security Review + Director approval.
""",
        encoding="utf-8",
    )

    # 7. Security Incidents & Phishing
    (docs_dir / "security_incidents.md").write_text(
        """# Information Security Incident Protocols

Our InfoSec team monitors endpoints 24/7. Prompt reporting prevents data breaches.

## Reporting Phishing & Social Engineering:
1. Do not click links or download attachments.
2. In Google Mail / Outlook, click the "Report Phishing" hook icon.
3. If you accidentally entered credentials or approved an MFA prompt:
   - Immediately disconnect Wi-Fi / Ethernet.
   - Contact InfoSec hotline: +1 (555) 019-9999 or message `#security-emergency`.
   - IT will initiate emergency password reset and revoke active session tokens.

## Lost or Stolen Laptop:
- Report immediately to `it-security@company.com`.
- IT will issue a remote wipe command via Jamf / InTune.
""",
        encoding="utf-8",
    )

    # 8. Department Metadata Mapping
    (docs_dir / "metadata.json").write_text(
        """{
  "vpn.md": {
    "departments": ["engineering", "it", "finance", "sales", "hr", "all"]
  },
  "gitlab.md": {
    "departments": ["engineering", "it"]
  },
  "wifi_network.md": {
    "departments": ["all"]
  },
  "sso_okta.md": {
    "departments": ["all"]
  },
  "hardware_laptop.md": {
    "departments": ["all"]
  },
  "software_requests.md": {
    "departments": ["engineering", "it", "all"]
  },
  "security_incidents.md": {
    "departments": ["all"]
  }
}
""",
        encoding="utf-8",
    )

    # Seed Historical Incidents in DB
    with Session(engine) as session:
        existing_tickets = {
            t.ticket_id for t in session.exec(select(Incident)).all()
        }

        seed_incidents = [
            Incident(
                ticket_id="INC-1001",
                title="GitLab unreachable over VPN",
                description="Engineer connected to VPN but could not reach internal GitLab on port 443.",
                resolution="VPN split-tunnel route was missing for 10.14.0.0/16; reconnecting the approved primary VPN profile restored proper routing.",
                department="engineering",
                status="resolved",
            ),
            Incident(
                ticket_id="INC-1002",
                title="VPN connected but internal DNS failed",
                description="Internal hostnames (*.corp.internal) did not resolve after VPN connection on macOS Sequoia.",
                resolution="Flushed local mDNSResponder cache and updated DNS search domains in Network settings.",
                department="all",
                status="resolved",
            ),
            Incident(
                ticket_id="INC-1003",
                title="Okta MFA push loop on new iPhone",
                description="Employee upgraded to iPhone 16 and stopped receiving push approvals from Okta Verify.",
                resolution="Reset user MFA factors in Okta Admin console and issued a temporary activation QR code.",
                department="all",
                status="resolved",
            ),
            Incident(
                ticket_id="INC-1004",
                title="BitLocker recovery key prompt on boot",
                description="Finance manager laptop prompted for 48-digit BitLocker recovery key after Dell BIOS firmware update.",
                resolution="Retrieved BitLocker recovery key from Azure AD Device Management and resumed normal boot.",
                department="finance",
                status="resolved",
            ),
            Incident(
                ticket_id="INC-1005",
                title="Docker Desktop licensing and daemon startup error",
                description="Developer received licensing violation banner and docker socket connection error.",
                resolution="Assigned Docker Business license in Docker Hub portal and allocated 8GB RAM in Docker settings.",
                department="engineering",
                status="resolved",
            ),
            Incident(
                ticket_id="INC-1006",
                title="Suspicious wire transfer phishing email received",
                description="Finance analyst received spoofed CEO request asking for urgent wire transfer.",
                resolution="Flagged email in Proofpoint email security filter and purged message from all employee mailboxes.",
                department="finance",
                status="resolved",
            ),
            Incident(
                ticket_id="INC-1007",
                title="External monitor flickering through Thunderbolt dock",
                description="Sales rep external 4K monitors going black intermittently every few minutes.",
                resolution="Replaced failing CalDigit Thunderbolt 4 cable and updated dock firmware.",
                department="sales",
                status="resolved",
            ),
            Incident(
                ticket_id="INC-1008",
                title="HR portal 403 Forbidden after department transition",
                description="HR business partner unable to view employee salary reviews after lateral department transfer.",
                resolution="Updated Workday RBAC security group assignment in Okta directory.",
                department="hr",
                status="resolved",
            ),
        ]

        added_count = 0
        for inc in seed_incidents:
            if inc.ticket_id not in existing_tickets:
                session.add(inc)
                added_count += 1
        session.commit()

    print(f"Seed complete. Ingested documentation and added {added_count} new historical incidents.")


if __name__ == "__main__":
    seed()
