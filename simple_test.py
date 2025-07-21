#!/usr/bin/env python3
"""
Simple test to check OpenAI API key
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_api_key():
    """Check API key format and basic info"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ No API key found")
        return
    
    print(f"🔑 API Key found: {api_key[:8]}...{api_key[-4:]}")
    print(f"📏 Length: {len(api_key)} characters")
    print(f"🎯 Starts with 'sk-': {api_key.startswith('sk-')}")
    
    # Test basic API call
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        print("\n🧪 Testing basic API call...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10
        )
        print("✅ API call successful!")
        print(f"📝 Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print("\n💡 Try these steps:")
        print("1. Go to https://platform.openai.com/account/api-keys")
        print("2. Create a new API key")
        print("3. Make sure you have credits in your account")
        print("4. Check if the key is from the right account")

if __name__ == "__main__":
    print("🔍 Simple OpenAI API Key Test")
    print("=" * 40)
    check_api_key() 