# Single Sign-On (Okta) & Multi-Factor Authentication

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
