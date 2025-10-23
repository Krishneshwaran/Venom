"""
Main Application - Live Chat with Gemini
Demonstrates different modes of interaction
"""

import asyncio
from live_chat_module import (
    start_live_video_chat,
    start_live_audio_chat,
    start_live_multimodal_chat,
    start_optimized_qa,
    get_live_chat_engine
)
from utils import log_info, log_success


def print_menu():
    """Display main menu"""
    print("\n" + "="*60)
    print("🤖 GEMINI LIVE CHAT - SELECT MODE")
    print("="*60)
    print("\n📹 VIDEO MODES:")
    print("  1. Live Video Chat (Real-time streaming)")
    print("  2. Optimized Video Q&A (Recommended - Less time consuming)")
    print("\n🎤 AUDIO MODE:")
    print("  3. Live Audio Chat (Voice conversation)")
    print("\n🎯 MULTIMODAL:")
    print("  4. Video + Audio Chat (Both together)")
    print("\n⚙️  OTHER:")
    print("  5. Exit")
    print("="*60)


async def main():
    """Main application entry point"""
    log_success("🚀 Gemini Live Chat System Started")
    
    while True:
        print_menu()
        
        try:
            choice = input("\n👉 Enter your choice (1-5): ").strip()
            
            if choice == '1':
                log_info("Starting Live Video Chat...")
                print("\n📹 Live Video Chat Mode")
                print("The camera will stream to Gemini in real-time")
                print("Press 'q' in the video window to quit\n")
                await start_live_video_chat()
            
            elif choice == '2':
                log_info("Starting Optimized Video Q&A...")
                print("\n⚡ Optimized Video Q&A Mode (RECOMMENDED)")
                print("Camera runs continuously, you ask questions via keyboard")
                print("This mode is FASTER and more efficient!")
                print("Type 'q' to quit, 'c' to clear screen\n")
                await start_optimized_qa()
            
            elif choice == '3':
                log_info("Starting Live Audio Chat...")
                print("\n🎤 Live Audio Chat Mode")
                print("Speak naturally, Gemini will respond")
                print("Press Ctrl+C to stop\n")
                await start_live_audio_chat()
            
            elif choice == '4':
                log_info("Starting Multimodal Chat...")
                print("\n🎯 Video + Audio Chat Mode")
                print("Both video and audio will be streamed")
                print("Press 'q' in video window or Ctrl+C to quit\n")
                await start_live_multimodal_chat()
            
            elif choice == '5':
                log_success("👋 Goodbye!")
                # Cleanup
                engine = get_live_chat_engine()
                engine.cleanup()
                break
            
            else:
                print("❌ Invalid choice. Please select 1-5")
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            engine = get_live_chat_engine()
            engine.cleanup()
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Returning to menu...\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Application closed")