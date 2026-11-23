# Laptop Hardware, BitLocker & FileVault Recovery

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
