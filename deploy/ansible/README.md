# Ansible deployment

```bash
cp inventory.example.ini inventory.ini
$EDITOR inventory.ini      # host(s), api key, browser on/off
ansible-playbook -i inventory.ini site.yml
```

Re-run to pull the latest commit and restart. `--limit <host>` to target one.

What it does: apt deps, `utilikit` user + dirs, clone, venv (`[browser,decode]`
or `[decode]`), optional Chromium download, render `/etc/utilikit/utilikit.env`
from the inventory, install + enable the systemd unit, health-check `:8400`.

Add more hosts under `[utilikit]` to run several instances.
