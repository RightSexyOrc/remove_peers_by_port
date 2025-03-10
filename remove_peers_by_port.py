#!/usr/bin/env python3

import subprocess
import re
import argparse
from typing import List, Tuple

def get_peer_connections() -> List[Tuple[str, str, int]]:
    """Get list of peer connections with their NodeID and ports."""
    try:
        # Run the peer list command
        result = subprocess.run(['aba', 'peer', '-c', 'full_node'], 
                              capture_output=True, text=True, check=True)
        
        connections = []
        lines = result.stdout.split('\n')
        
        # Skip header lines
        for line in lines[2:]:  # Skip "Connections:" and header line
            # Match FULL_NODE entries with NodeID and port info
            match = re.match(r'FULL_NODE\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)/\d+\s+([a-f0-9]{8}).*', line)
            if match:
                ip, port, node_id = match.groups()
                connections.append((node_id, ip, int(port)))
                
        return connections
    except subprocess.CalledProcessError as e:
        print(f"Error running 'aba peer' command: {e}")
        return []

def remove_connection(node_id: str) -> bool:
    """Remove a connection by its NodeID."""
    try:
        subprocess.run(['aba', 'peer', '-r', node_id, "full_node"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error removing peer {node_id}: {e}")
        return False

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Remove connections using port 8444')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Show what would be removed without actually removing')
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN: Scanning for port 8444 connections (no connections will be removed)...")
    else:
        print("Scanning for port 8444 connections...")
    
    # Get all peer connections
    connections = get_peer_connections()
    
    # Filter and remove 8444 connections
    found_count = 0
    removed_count = 0
    
    for node_id, ip, port in connections:
        if port == 8444:
            found_count += 1
            if args.dry_run:
                print(f"Would remove: {ip}:{port} (NodeID: {node_id})")
            else:
                print(f"Found port 8444 connection: {ip}:{port} (NodeID: {node_id})")
                if remove_connection(node_id):
                    print(f"Successfully removed connection to {ip}")
                    removed_count += 1
                else:
                    print(f"Failed to remove connection to {ip}")
    
    if found_count == 0:
        print("No port 8444 connections found.")
    else:
        if args.dry_run:
            print(f"\nFound {found_count} connection(s) using port 8444 that would be removed.")
            print("Run without --dry-run to actually remove these connections.")
        else:
            print(f"\nRemoved {removed_count} out of {found_count} connection(s) using port 8444.")

if __name__ == "__main__":
    main()
