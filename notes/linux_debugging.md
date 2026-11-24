# Linux service troubleshooting

## Trace a failed systemd unit

Run `systemctl status photo-indexer.service --no-pager -l` for the exit status and recent messages. Then read the current boot's service log with `sudo journalctl -u photo-indexer.service -b --since "15 minutes ago" --no-pager`. Start at the first error before the restart loop. If the failure happened before a reboot, use `-b -1` and remove the time filter. The previous boot must still be in the journal.

Run `systemctl cat photo-indexer.service` to see the unit and its drop-ins. After changing a unit file, run `sudo systemctl daemon-reload` before restarting. If the log reports repeated starts too quickly, fix the underlying error, run `sudo systemctl reset-failed photo-indexer.service`, then restart and check the journal again.

## Repair script execution permissions

An exit status of `203/EXEC` means systemd could not execute the configured program. For an `ExecStart` that directly invokes `/opt/photo-indexer/bin/scan.sh`, inspect the script and each parent directory with `namei -l /opt/photo-indexer/bin/scan.sh`. The service account needs traverse permission on the directories and read and execute permission on the script.

For this deployment, the script belongs to `root:photos` and the service runs in the `photos` group. Apply `sudo chmod 0750 /opt/photo-indexer/bin/scan.sh` to grant the group read and execute access. Check that the shebang names an installed interpreter and that the file uses Unix line endings. Use `findmnt -T /opt/photo-indexer/bin/scan.sh -o TARGET,OPTIONS` to detect a `noexec` mount.

## Identify the listener on TCP port 8080

When startup fails with “Address already in use,” run `sudo ss -ltnp 'sport = :8080'` to identify the listening address and process. Cross-check the PID with `sudo lsof -nP -iTCP:8080 -sTCP:LISTEN`. Use `systemctl status 4321` to identify the owning systemd unit if the listener has PID 4321. If it belongs to a stale duplicate service, stop that unit and confirm the socket is free. If the listener is required, assign the incoming service another port and update its proxy or health check.

## Distinguish old swap use from active pressure

Run `free -h` and `swapon --show` to see available RAM and swap allocation. A host can have 2.1 GiB in swap while still serving normally. Sample `vmstat 1 10` and ignore the first report, which summarizes activity since boot. Repeated nonzero `si` and `so` alongside low available memory and rising latency suggest active memory pressure. Use `ps -eo pid,comm,rss --sort=-rss | head -n 11` to find large resident processes. Inspect `VmSwap` in `/proc/4321/status` for a suspect process to see its reported swap use.
