#!/usr/bin/env python3
"""
Test script for PodBroadcast server.
This script tests the HTTP server functionality without requiring podman.
"""

import os
import sys
import subprocess
import time
import urllib.request
import urllib.error
from multiprocessing import Process


def mock_podman_command():
    """Create a mock podman script for testing."""
    mock_script = """#!/bin/bash
# Mock podman command for testing
if [ "$1" = "ps" ] && [ "$2" = "-a" ] && [ "$3" = "--format" ] && [ "$4" = "json" ]; then
    echo '[{"Id":"test123","Names":["test-container"],"Image":"nginx:latest","Status":"Up 1 hour","State":"running"}]'
else
    echo "Unknown command: $@" >&2
    exit 1
fi
"""
    
    # Create mock podman in /tmp
    mock_podman_path = '/tmp/podman'
    with open(mock_podman_path, 'w') as f:
        f.write(mock_script)
    os.chmod(mock_podman_path, 0o755)
    
    return mock_podman_path


def start_server(api_key='test-key-123'):
    """Start the PodBroadcast server in a subprocess."""
    env = os.environ.copy()
    env['PODBROADCAST_KEY'] = api_key
    env['PODBROADCAST_HOST'] = '127.0.0.1'
    env['PODBROADCAST_PORT'] = '18080'
    env['PATH'] = '/tmp:' + env.get('PATH', '')  # Add /tmp to PATH for mock podman
    
    proc = subprocess.Popen(
        [sys.executable, 'podbroadcast.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    return proc


def test_unauthorized_access():
    """Test that requests without API key are rejected."""
    print("Test 1: Unauthorized access (no key)...")
    try:
        response = urllib.request.urlopen('http://127.0.0.1:18080/')
        print("  ✗ FAILED: Should have returned 401")
        return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("  ✓ PASSED: Correctly rejected unauthorized request")
            return True
        else:
            print(f"  ✗ FAILED: Unexpected error code {e.code}")
            return False


def test_wrong_key():
    """Test that requests with wrong API key are rejected."""
    print("Test 2: Wrong API key...")
    try:
        response = urllib.request.urlopen('http://127.0.0.1:18080/?key=wrong-key')
        print("  ✗ FAILED: Should have returned 401")
        return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("  ✓ PASSED: Correctly rejected wrong API key")
            return True
        else:
            print(f"  ✗ FAILED: Unexpected error code {e.code}")
            return False


def test_authorized_access():
    """Test that requests with correct API key work."""
    print("Test 3: Authorized access (correct key)...")
    try:
        response = urllib.request.urlopen('http://127.0.0.1:18080/?key=test-key-123')
        data = response.read().decode('utf-8')
        
        # Check if response is valid JSON
        import json
        parsed = json.loads(data)
        
        if isinstance(parsed, list) and len(parsed) > 0:
            print("  ✓ PASSED: Received valid JSON response")
            print(f"    Response: {data[:100]}...")
            return True
        else:
            print("  ✗ FAILED: Invalid response format")
            return False
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("PodBroadcast Test Suite")
    print("=" * 60)
    
    # Create mock podman
    print("\nSetting up mock podman...")
    mock_podman_path = mock_podman_command()
    print(f"  Mock podman created at: {mock_podman_path}")
    
    # Start server
    print("\nStarting server...")
    server_proc = start_server()
    
    if server_proc.poll() is not None:
        stdout, stderr = server_proc.communicate()
        print("  ✗ Server failed to start!")
        print("  STDOUT:", stdout.decode())
        print("  STDERR:", stderr.decode())
        return 1
    
    print("  ✓ Server started")
    
    try:
        # Run tests
        print("\nRunning tests...")
        results = [
            test_unauthorized_access(),
            test_wrong_key(),
            test_authorized_access(),
        ]
        
        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        if passed == total:
            print("✓ All tests passed!")
            return 0
        else:
            print("✗ Some tests failed")
            return 1
            
    finally:
        # Clean up
        print("\nCleaning up...")
        server_proc.terminate()
        server_proc.wait(timeout=5)
        os.remove(mock_podman_path)
        print("  ✓ Server stopped and mock cleaned up")


if __name__ == '__main__':
    sys.exit(main())
