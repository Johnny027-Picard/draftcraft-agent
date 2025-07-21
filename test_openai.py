#!/usr/bin/env python3
"""
Test script to verify OpenAI API key is working
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_key():
    """Test if OpenAI API key is valid and working"""
    
    # Get API key from environment
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("\n📝 To fix this:")
        print("1. Create a .env file in your project root")
        print("2. Add: OPENAI_API_KEY=your_actual_api_key_here")
        print("3. Or set it in your system environment variables")
        print("\n🔑 Your API key should start with 'sk-' and be about 51 characters long")
        return False
    
    print(f"🔑 Found API key: {api_key[:8]}...{api_key[-4:]}")
    
    # Validate key format
    if not api_key.startswith('sk-'):
        print("❌ API key format looks incorrect - should start with 'sk-'")
        return False
    
    if len(api_key) < 40:
        print("❌ API key seems too short - should be about 51 characters")
        return False
    
    # Configure OpenAI client
    client = OpenAI(api_key=api_key)
    
    try:
        # Test with a simple completion
        print("🧪 Testing OpenAI API...")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'Hello, this is a test!' and nothing else."}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ API test successful!")
        print(f"📝 Response: {result}")
        
        # Test with a more complex prompt to verify full functionality
        print("\n🧪 Testing proposal generation...")
        
        test_prompt = """Generate a brief business proposal for a web development service. 
        Keep it under 100 words and professional."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": test_prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        proposal = response.choices[0].message.content.strip()
        print(f"✅ Proposal generation test successful!")
        print(f"📝 Sample proposal: {proposal[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if "invalid_api_key" in str(e).lower():
            print("\n💡 This usually means:")
            print("1. The API key is incorrect")
            print("2. The key has expired or been revoked")
            print("3. You need to check your OpenAI account at https://platform.openai.com/account/api-keys")
        return False

if __name__ == "__main__":
    print("🚀 Testing OpenAI API Key...")
    print("=" * 50)
    
    success = test_openai_key()
    
    print("=" * 50)
    if success:
        print("🎉 All tests passed! Your OpenAI API key is working correctly.")
    else:
        print("💥 Tests failed. Please check your API key and try again.") 