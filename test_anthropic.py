#!/usr/bin/env python3
"""
Test script to verify Anthropic SDK installation
"""

def test_anthropic_installation():
    """Test if anthropic package is installed and can be imported"""
    print("Testing Anthropic SDK installation...")
    print("-" * 50)
    
    # Test 1: Try to import the package
    try:
        import anthropic
        print("[OK] Successfully imported 'anthropic' package")
    except ImportError as e:
        print(f"X Failed to import 'anthropic' package: {e}")
        print("\nTo install, run: pip install anthropic")
        return False
    
    # Test 2: Check version
    try:
        version = anthropic.__version__
        print(f"[OK] Anthropic version: {version}")
    except AttributeError:
        print("! Version information not available")
    
    # Test 3: Try to create a client instance (without API key)
    try:
        client = anthropic.Anthropic(api_key="test-key")
        print("[OK] Successfully created Anthropic client instance")
    except Exception as e:
        print(f"! Could not create client instance: {e}")
    
    # Test 4: Check if main classes are available
    try:
        from anthropic import Anthropic
        print("[OK] Anthropic class is available")
    except ImportError as e:
        print(f"X Could not import Anthropic class: {e}")
        return False
    
    print("-" * 50)
    print("[OK] Anthropic SDK appears to be correctly installed!")
    return True

if __name__ == "__main__":
    success = test_anthropic_installation()
    exit(0 if success else 1)

