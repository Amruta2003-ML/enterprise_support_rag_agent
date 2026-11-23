# Corporate VPN Troubleshooting Guide

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
