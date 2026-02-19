#!/usr/bin/env python3
"""
TEST 1: Algo Server & Client Connection Test
Tests if RPi can connect to Algo server on PC and request path
"""

import sys
import json
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent))

from RPI_v1.communication.algo_client import AlgoClient


def test_algo():
    """Test Algo client-server connection"""

    print("\n" + "="*80)
    print("ALGO SERVER & CLIENT TEST")
    print("="*80)
    print("\nStep 1: Verify algo_server.py is running on PC")
    print("  Command on PC: python Algo/algo_server.py")
    print("  You should see: [AlgoServer] Listening on 0.0.0.0:6000")
    input("\nPress ENTER when algo_server is running on PC...")

    print("\n" + "-"*80)
    print("Step 2: Testing connection to Algo server...")
    print("-"*80)

    try:
        client = AlgoClient(host='192.168.88.3', port=6000)
        print(f"[TEST] Connecting to Algo server at 192.168.88.3:6000...")
        client.connect()
        print("✓ Connected successfully!\n")

    except Exception as e:
        print(f"✗ FAILED: {e}\n")
        print("Troubleshooting:")
        print("  1. Make sure algo_server.py is running on PC")
        print("  2. Check PC IP: on PC terminal, run 'ipconfig' or 'ifconfig'")
        print("  3. Check if 192.168.88.3 is correct (update if needed)")
        print("  4. Make sure both devices are on same WiFi")
        print("  5. Check firewall isn't blocking port 6000")
        return False

    print("-"*80)
    print("Step 3: Creating test arena data...")
    print("-"*80)

    # Create test data using SAME obstacles as Algo/main.py task_1()
    # This is the exact arena setup you've been testing locally
    test_data = {
        'grid_size': {'x': 40, 'y': 40},
        'robot': {
            'x': 3,
            'y': 3,
            'd': 0  # NORTH
        },
        'obstacles': [
            {'id': 1, 'x': 2, 'y': 15, 'width': 2, 'length': 2, 'd': 4},   # SOUTH
            {'id': 2, 'x': 16, 'y': 4, 'width': 2, 'length': 2, 'd': 2},   # EAST
            {'id': 3, 'x': 34, 'y': 4, 'width': 2, 'length': 2, 'd': 0},   # NORTH
            {'id': 4, 'x': 29, 'y': 16, 'width': 2, 'length': 2, 'd': 0},  # NORTH
            {'id': 5, 'x': 13, 'y': 24, 'width': 2, 'length': 2, 'd': 2},  # EAST
            {'id': 6, 'x': 4, 'y': 35, 'width': 2, 'length': 2, 'd': 4},   # SOUTH
            {'id': 7, 'x': 18, 'y': 35, 'width': 2, 'length': 2, 'd': 2},  # EAST
            {'id': 8, 'x': 34, 'y': 35, 'width': 2, 'length': 2, 'd': 6},  # WEST
        ]
        # NOTE: No parking in task_1, so removed from test
    }

    print("Test arena data (from Algo/main.py task_1):")
    print(f"  Grid: 40x40 cells")
    print(f"  Robot: ({test_data['robot']['x']}, {test_data['robot']['y']}), facing NORTH")
    print(f"  Obstacles: {len(test_data['obstacles'])} total")
    direction_map = {0: "NORTH", 2: "EAST", 4: "SOUTH", 6: "WEST"}
    for obs in test_data['obstacles']:
        d_name = direction_map.get(obs['d'], str(obs['d']))
        print(f"    - Obstacle {obs['id']} at ({obs['x']:2d}, {obs['y']:2d}) facing {d_name}")

    print("\n" + "-"*80)
    print("Step 4: Sending arena data to Algo server...")
    print("-"*80)

    try:
        path = client.send_arena_data(test_data)
        print(f"✓ Received path with {len(path)} waypoints!\n")

    except Exception as e:
        print(f"✗ FAILED: {e}")
        print("\nPossible issues:")
        print("  - Algo server crashed (check PC terminal)")
        print("  - Invalid arena data format")
        print("  - Network connection lost")
        client.disconnect()
        return False

    print("-"*80)
    print("Step 5: Analyzing returned path...")
    print("-"*80)

    print(f"\nTotal waypoints: {len(path)}")
    print(f"\nFirst 5 waypoints:")
    for i, wp in enumerate(path[:5]):
        d_name = {0: "NORTH", 2: "EAST", 4: "SOUTH", 6: "WEST"}.get(wp['d'], str(wp['d']))
        s_name = f"SCREENSHOT({wp['s']})" if wp['s'] >= 0 else "no screenshot"
        print(f"  {i+1}. Position ({wp['x']:2d}, {wp['y']:2d}) facing {d_name:5s} - {s_name}")

    if len(path) > 5:
        print(f"  ... ({len(path) - 10} more waypoints) ...")

    print(f"\nLast 2 waypoints:")
    for i, wp in enumerate(path[-2:], start=len(path)-1):
        d_name = {0: "NORTH", 2: "EAST", 4: "SOUTH", 6: "WEST"}.get(wp['d'], str(wp['d']))
        s_name = f"SCREENSHOT({wp['s']})" if wp['s'] >= 0 else "no screenshot"
        print(f"  {i+1}. Position ({wp['x']:2d}, {wp['y']:2d}) facing {d_name:5s} - {s_name}")

    # Check for screenshots
    screenshots = [wp for wp in path if wp['s'] >= 0]
    print(f"\nScreenshots needed: {len(screenshots)}")
    if screenshots:
        print("  Waypoints where car should take photos:")
        for wp in screenshots:
            print(f"    - Obstacle {wp['s']} at position ({wp['x']}, {wp['y']})")

    client.disconnect()

    print("\n" + "="*80)
    print("✓ TEST PASSED - Algo communication works!")
    print("="*80 + "\n")
    return True


if __name__ == "__main__":
    success = test_algo()
    sys.exit(0 if success else 1)
