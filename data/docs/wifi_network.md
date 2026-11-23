# Office Wi-Fi & Wired Network Access

The enterprise maintains three wireless networks:
- **Corp-Secure:** For managed laptops only. Uses 802.1X EAP-TLS certificate authentication.
- **Corp-Guest:** For visitors and contractor personal devices. Requires captive portal phone validation.
- **IoT-Hardware:** Dedicated for test benches and smart displays (MAC address whitelisted).

## Troubleshooting "Corp-Secure" Connection Failures
1. Forget the network "Corp-Secure" in your operating system Wi-Fi settings.
2. Reconnect and select certificate authentication (select your user certificate issued by Corp-CA).
3. If no certificate is found, run the InTune/Jamf Self-Service app and run "Renew Wi-Fi Certificates".
4. Ensure your machine's clock is synchronized with NTP (`time.windows.com` or `time.apple.com`).
