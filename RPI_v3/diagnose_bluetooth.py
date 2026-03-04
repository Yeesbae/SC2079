#!/usr/bin/env python3
"""
Comprehensive Bluetooth Diagnostic for Raspberry Pi
Checks all common issues with Bluetooth setup on RPi OS Bookworm
"""
import subprocess
import os
import sys

def run_cmd(cmd, timeout=10):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", 1
    except Exception as e:
        return "", str(e), 1

def check_status(name, condition, fix=""):
    """Print status check result"""
    if condition:
        print(f"  ✓ {name}")
        return True
    else:
        print(f"  ✗ {name}")
        if fix:
            print(f"    FIX: {fix}")
        return False

def main():
    print("=" * 70)
    print("Raspberry Pi Bluetooth Diagnostic Tool")
    print("=" * 70)
    
    all_ok = True
    fixes_needed = []
    
    # =========================================================================
    # 1. Check if running on RPi
    # =========================================================================
    print("\n[1] System Check")
    out, _, _ = run_cmd("cat /proc/device-tree/model 2>/dev/null")
    if "Raspberry Pi" in out:
        print(f"  ✓ Running on: {out}")
    else:
        print(f"  ? System: {out if out else 'Unknown (not RPi?)'}")
    
    # Check OS version
    out, _, _ = run_cmd("cat /etc/os-release | grep PRETTY_NAME")
    if out:
        print(f"  ℹ {out}")
    
    # =========================================================================
    # 2. Check Bluetooth packages
    # =========================================================================
    print("\n[2] Required Packages")
    
    packages = {
        'bluez': 'sudo apt install bluez',
        'bluetooth': 'sudo apt install bluetooth',
        'python3-bluez': 'sudo apt install python3-bluez',
    }
    
    for pkg, fix in packages.items():
        out, _, code = run_cmd(f"dpkg -l | grep -w {pkg}")
        if code == 0 and out:
            check_status(f"{pkg} installed", True)
        else:
            check_status(f"{pkg} installed", False, fix)
            fixes_needed.append(fix)
            all_ok = False
    
    # Check pybluez Python module
    try:
        import bluetooth
        check_status("pybluez Python module", True)
    except ImportError:
        check_status("pybluez Python module", False, "pip install pybluez OR sudo apt install python3-bluez")
        fixes_needed.append("sudo apt install python3-bluez")
        all_ok = False
    
    # =========================================================================
    # 3. Check Bluetooth services
    # =========================================================================
    print("\n[3] Bluetooth Services")
    
    # Main bluetooth service
    out, _, _ = run_cmd("systemctl is-active bluetooth")
    if not check_status("bluetooth.service active", out == "active", "sudo systemctl start bluetooth"):
        fixes_needed.append("sudo systemctl enable --now bluetooth")
        all_ok = False
    
    # Check if bluetooth is blocked
    out, _, _ = run_cmd("rfkill list bluetooth")
    if "Soft blocked: yes" in out or "Hard blocked: yes" in out:
        check_status("Bluetooth not blocked", False, "sudo rfkill unblock bluetooth")
        fixes_needed.append("sudo rfkill unblock bluetooth")
        all_ok = False
    else:
        check_status("Bluetooth not blocked", True)
    
    # =========================================================================
    # 4. Check Bluetooth adapter
    # =========================================================================
    print("\n[4] Bluetooth Adapter")
    
    out, _, _ = run_cmd("hciconfig")
    if "hci0" in out:
        check_status("Bluetooth adapter (hci0) found", True)
        if "UP RUNNING" in out:
            check_status("Adapter is UP and RUNNING", True)
        else:
            check_status("Adapter is UP and RUNNING", False, "sudo hciconfig hci0 up")
            fixes_needed.append("sudo hciconfig hci0 up")
            all_ok = False
    else:
        check_status("Bluetooth adapter found", False, "Check if Bluetooth hardware is enabled")
        all_ok = False
    
    # Get adapter address
    out, _, _ = run_cmd("hciconfig hci0 | grep 'BD Address'")
    if out:
        print(f"  ℹ {out.strip()}")
    
    # =========================================================================
    # 5. Check bluetoothctl status
    # =========================================================================
    print("\n[5] Bluetooth Controller Status")
    
    out, _, _ = run_cmd("bluetoothctl show")
    
    if "Powered: yes" in out:
        check_status("Controller powered on", True)
    else:
        check_status("Controller powered on", False, "bluetoothctl power on")
        fixes_needed.append("bluetoothctl power on")
        all_ok = False
    
    if "Discoverable: yes" in out:
        check_status("Controller discoverable", True)
    else:
        check_status("Controller discoverable", False, "bluetoothctl discoverable on")
        print("    NOTE: Discoverable mode helps PC find RPi")
    
    if "Pairable: yes" in out:
        check_status("Controller pairable", True)
    else:
        check_status("Controller pairable", False, "bluetoothctl pairable on")
    
    # =========================================================================
    # 6. Check SDP (Service Discovery Protocol) - CRITICAL for RFCOMM
    # =========================================================================
    print("\n[6] SDP Service (Required for RFCOMM)")
    
    # Check if bluetooth daemon runs with compatibility mode
    out, _, _ = run_cmd("cat /lib/systemd/system/bluetooth.service | grep ExecStart")
    
    if "--compat" in out or "-C" in out:
        check_status("Bluetooth in compatibility mode", True)
    else:
        check_status("Bluetooth in compatibility mode", False, 
                    "Edit /lib/systemd/system/bluetooth.service and add '-C' or '--compat' to ExecStart")
        fixes_needed.append("MANUAL: Add '--compat' flag to bluetooth.service (see below)")
        all_ok = False
    
    # Check if SDP socket exists
    out, _, code = run_cmd("ls -la /var/run/sdp 2>/dev/null")
    if code == 0:
        check_status("SDP socket exists", True)
    else:
        check_status("SDP socket exists", False, "Need to enable compatibility mode (see above)")
        all_ok = False
    
    # =========================================================================
    # 7. Check permissions
    # =========================================================================
    print("\n[7] Permissions")
    
    user = os.environ.get('USER', 'unknown')
    out, _, _ = run_cmd(f"groups {user}")
    
    if "bluetooth" in out:
        check_status(f"User '{user}' in bluetooth group", True)
    else:
        check_status(f"User '{user}' in bluetooth group", False, 
                    f"sudo usermod -a -G bluetooth {user} && logout/login")
        fixes_needed.append(f"sudo usermod -a -G bluetooth {user}")
        all_ok = False
    
    # =========================================================================
    # 8. Check paired devices
    # =========================================================================
    print("\n[8] Paired Devices")
    
    out, _, _ = run_cmd("bluetoothctl devices Paired")
    if out:
        print(f"  ℹ Paired devices:\n    {out.replace(chr(10), chr(10) + '    ')}")
    else:
        print("  ℹ No paired devices")
    
    # =========================================================================
    # Summary and fixes
    # =========================================================================
    print("\n" + "=" * 70)
    
    if all_ok:
        print("✓ All checks passed! Bluetooth should be working.")
        print("\nIf connections still fail, ensure:")
        print("  1. Your PC/Android is trying to CONNECT to RPi (RPi is server)")
        print("  2. The PC knows RPi's MAC address")
        print("  3. PC has paired with RPi first")
    else:
        print("✗ Issues found! Run these fixes:")
        print()
        
        # Deduplicate fixes
        seen = set()
        for fix in fixes_needed:
            if fix not in seen:
                print(f"  {fix}")
                seen.add(fix)
        
        # Special instruction for compatibility mode
        if "MANUAL:" in str(fixes_needed):
            print("\n" + "-" * 70)
            print("IMPORTANT: Enable Bluetooth Compatibility Mode (required for RFCOMM):")
            print("-" * 70)
            print("""
1. Edit the bluetooth service file:
   sudo nano /lib/systemd/system/bluetooth.service

2. Find the line that starts with 'ExecStart=' and add '--compat':
   ExecStart=/usr/libexec/bluetooth/bluetoothd --compat

3. Reload and restart:
   sudo systemctl daemon-reload
   sudo systemctl restart bluetooth

4. Add SDP socket permissions (may need this on some systems):
   sudo chmod 777 /var/run/sdp
""")
    
    # =========================================================================
    # Quick fix script
    # =========================================================================
    print("\n" + "=" * 70)
    create_fix = input("Create auto-fix script? (y/n): ").strip().lower()
    
    if create_fix == 'y':
        fix_script = """#!/bin/bash
# Bluetooth Auto-Fix Script for Raspberry Pi

echo "=== Bluetooth Auto-Fix Script ==="

# Install packages
echo "[1] Installing required packages..."
sudo apt update
sudo apt install -y bluez bluetooth python3-bluez

# Unblock Bluetooth
echo "[2] Unblocking Bluetooth..."
sudo rfkill unblock bluetooth

# Enable compatibility mode
echo "[3] Enabling compatibility mode..."
sudo sed -i 's|ExecStart=/usr/libexec/bluetooth/bluetoothd|ExecStart=/usr/libexec/bluetooth/bluetoothd --compat|g' /lib/systemd/system/bluetooth.service

# Reload and restart
echo "[4] Restarting Bluetooth service..."
sudo systemctl daemon-reload
sudo systemctl restart bluetooth
sleep 2

# Power on and make discoverable
echo "[5] Configuring Bluetooth controller..."
sudo bluetoothctl power on
sudo bluetoothctl discoverable on
sudo bluetoothctl pairable on
sudo bluetoothctl agent on
sudo bluetoothctl default-agent

# Add user to bluetooth group
echo "[6] Adding user to bluetooth group..."
sudo usermod -a -G bluetooth $USER

# Bring up adapter
echo "[7] Bringing up adapter..."
sudo hciconfig hci0 up

echo ""
echo "=== Done! ==="
echo "You may need to logout and login for group changes to take effect."
echo "Then run: python3 test_bt_simple.py"
"""
        with open("fix_bluetooth.sh", "w") as f:
            f.write(fix_script)
        os.chmod("fix_bluetooth.sh", 0o755)
        print("\n✓ Created 'fix_bluetooth.sh'")
        print("  Run: sudo ./fix_bluetooth.sh")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
