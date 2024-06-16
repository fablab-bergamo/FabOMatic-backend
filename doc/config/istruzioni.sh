systemctl --user enable --now FabOMatic.service
loginctl enable-linger
systemctl --user status FabOMatic.service
