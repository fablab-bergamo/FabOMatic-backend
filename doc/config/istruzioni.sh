systemctl --user enable --now FabOMatic.service
loginctl enable-linger
systemctl --user status FabOMatic.service

sudo visudo
# Add line to allow reboot by UI
# your_username ALL=(ALL) NOPASSWD: /sbin/reboot