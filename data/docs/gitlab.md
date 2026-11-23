# Internal GitLab & Code Repository Access Guide

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
