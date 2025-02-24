#!/usr/bin/env python3

import subprocess
import re
import argparse
import ipaddress
import shutil
from typing import List, Tuple

INTRODUCERS = ('dns-introducer.abacoin.net', 'dns-introducer.aba-project.io', 'dns-introducer.aba.ooo', 'dns-introducer.abacoin.io')

def check_commands():
    for cmd in ['aba', 'dig']:
        if not shutil.which(cmd):
            print(f"Error: '{cmd}' command not found. Please ensure it is installed and in and the venv is active.")
            exit(1)

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
            match = re.match(r'FULL_NODE\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)/\d+\s+([a-f0-9]{8}).*', line.strip())
            if match:
                ip, port, node_id = match.groups()
                connections.append((node_id, ip, int(port)))
                
        return connections
    except subprocess.CalledProcessError as e:
        print(f"Error running 'aba peer' command: {e}")
        return []

def dig_new_peers (existing_connections: List[Tuple[str, str, int]], port: int) -> List:
    """Dig list of aba peers from introducer."""
    try:
        # Initialize output
        connections = set()
        
        # Run dig on introducers
        for introducer in INTRODUCERS:
            # Use +short to only get the IP address so we don't have to mess with the header/footer
            result = subprocess.run(['dig', introducer, '+short'], 
                                    capture_output=True, text=True, check=True)
            lines = result.stdout.split('\n')
            for line in lines:
                # Check if peer exists as aba peer
                if line and not check_existing_aba_peer(line, existing_connections, port):
                    connections.add(line)
        return list(connections)
    except subprocess.CalledProcessError as e:
        print(f"Error running 'dig' command: {e}")
        return []

def check_existing_aba_peer(new_ip: str, connections: List[Tuple[str, str, int]], new_port: int) -> bool:
    """Check if an ip is already connected on args.replace_port"""
    for node_id, ip, port in connections:
        if port == new_port and ip == new_ip:
            return True
    return False

def remove_connection(node_id: str) -> bool:
    """Remove a connection by its NodeID."""
    try:
        result = subprocess.run(['aba', 'peer', '-r', node_id, 'full_node'], 
                                capture_output=True, text=True, check=True)
        print(result.stdout)
        if "disconnected" in result.stdout.lower():
            return True
        print(f"Failed to remove peer {node_id}: {result.stderr}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error removing peer {node_id}: {e}")
        return False

def is_valid_ip(ip: str) -> bool:
    """Validates the input is a valid IP Address"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def add_peer(ip: str, port: int) -> bool:
    """Add a new peer"""
    if not is_valid_ip(ip):
        print(f"Invalid IP address: {ip}")
        return False
    try:
        peer = f"{ip}:{port}"
        result = subprocess.run(['aba', 'peer', '-a', peer, 'full_node'], 
                                capture_output=True, text=True, check=True)
        print (result.stdout)
        if not "failed" in result.stdout.lower():
            return True
        print(f"Failed to add peer {peer}: {result.stderr}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error adding peer {peer}: {e}")
        return False

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Remove connections using the specified port (default=8444)')
    parser.add_argument('--dry-run', '-d', action='store_true',
                       help='Show what would be removed without actually removing')
    parser.add_argument('--replace', '-r', action='store_true',
                       help='Replace any peers on the specified port (default=8444) with a new peer on the specified port (default=port 8644)')
    parser.add_argument('--remove-port', type=int, default=8444, help='Port to remove peers from')
    parser.add_argument('--replace-port', type=int, default=8644, help='Port for replacement peers')

    args = parser.parse_args()

    # Verify venv is active and dig is installed
    check_commands()
    
    if args.dry_run:
        print(f"DRY RUN: Scanning for port {args.remove_port} connections (no connections will be removed)...")
        if args.replace:
            print("DRY RUN: REPLACE: Finding replacement peers (no connections will be replace)...")
    else:
        print(f"Scanning for port {args.remove_port} connections...")
        if args.replace:
            print ("Finding replacement peers...")
    
    
    # Get all peer connections
    connections = get_peer_connections()
    
    # Find replacement peers
    new_peers = dig_new_peers (connections, args.replace_port)
    
    # Filter and remove args.remove_port connections
    found_count = 0
    removed_count = 0
    replaced_count = 0
    
    for node_id, ip, port in connections:
        if port == args.remove_port:
            found_count += 1
            if args.dry_run:
                print(f"Would remove: {ip}:{port} (NodeID: {node_id})")
                if args.replace and new_peers:
                    print(f"Would replace with: {new_peers.pop(0)}")
            else:
                print(f"Found port {args.remove_port} connection: {ip}:{port} (NodeID: {node_id})")
                if remove_connection(node_id):
                    print(f"Successfully removed connection to {ip}")
                    removed_count += 1
                    if args.replace and new_peers:
                        new_peer = new_peers.pop(0)
                        print(f"Trying to connect to {new_peer}:{args.replace_port}.")
                        success = add_peer(new_peer, args.replace_port)
                        while new_peers and not success:
                            print(f"Failed to add {new_peer}:{args.replace_port}.")
                            new_peer = new_peers.pop(0)
                            print(f"Trying to connect to {new_peer}:{args.replace_port}.")
                            success = add_peer(new_peer, args.replace_port)
                        if success:
                            print(f"Successfully replaced connection {ip} with {new_peer}")
                            replaced_count += 1
                        else:
                            print(f"Failed to replace connection {ip} with {new_peer}")
                    else:
                            print(f"No replacement peers available")
                else:
                    print(f"Failed to remove connection to {ip}")
    
    if found_count == 0:
        print(f"No port {args.remove_port} connections found.")
    else:
        if args.dry_run:
            print(f"\nFound {found_count} connection(s) using port {args.remove_port} that would be removed.")
            print("Run without --dry-run to actually remove these connections.")
        else:
            print(f"\nRemoved {removed_count} out of {found_count} connection(s) using port {args.remove_port}.")
            print(f"\nReplaced {replaced_count} out of {found_count} connection(s) using port {args.remove_port} with new peers on port {args.replace_port}.")

if __name__ == "__main__":
    main()
