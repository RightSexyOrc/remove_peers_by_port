For Ubuntu

Remove connections to full node peers on port 8444 for Aba

Make sure to activate aba-blockchain venv first (i.e. . ./activate in aba-blockchain dir)

```
# Dry run - just show what would be removed
./remove_8444_peers.py --dry-run

# Actually remove the connections
./remove_8444_peers.py
```
