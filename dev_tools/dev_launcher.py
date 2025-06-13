#!/usr/bin/env python3
"""
Custom Tests Battery - Development Launcher
Cross-platform development runner with auto-reload
"""

import sys
import os
import time
import subprocess
import threading
from pathlib import Path

# Add parent directory to path so we can import the main app
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check for watchdog, install if missing
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    print("📦 Installing watchdog for auto-reload...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "watchdog"])
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True

class AppReloader(FileSystemEventHandler):
    def __init__(self, app_process_ref):
        self.app_process_ref = app_process_ref
        self.last_reload = 0
        self.reload_delay = 1.0
        
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
            
        # Ignore changes in dev_tools folder to prevent infinite loops
        if 'dev_tools' in event.src_path:
            return
            
        current_time = time.time()
        if current_time - self.last_reload < self.reload_delay:
            return
            
        print(f"\n🔄 File changed: {os.path.basename(event.src_path)}")
        print("Reloading application...")
        
        # Terminate current process
        if self.app_process_ref[0] and self.app_process_ref[0].poll() is None:
            self.app_process_ref[0].terminate()
            try:
                self.app_process_ref[0].wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.app_process_ref[0].kill()
        
        # Start new process
        self.app_process_ref[0] = start_app()
        self.last_reload = current_time

def start_app():
    """Start the application in executable-like environment"""
    # Get the parent directory (where welcome.py is located)
    app_dir = Path(__file__).parent.parent
    
    env = os.environ.copy()
    env['PYTHONPATH'] = str(app_dir)
    env['APP_DEV_MODE'] = 'true'
    env['APP_SIMULATE_FROZEN'] = 'true'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    
    cmd = [sys.executable, str(app_dir / 'welcome.py')]
    
    # Platform-specific process creation
    if sys.platform == 'win32':
        # Windows: Hide console window for cleaner testing
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return subprocess.Popen(cmd, env=env, startupinfo=startupinfo, cwd=app_dir)
    else:
        # macOS/Linux: Standard process
        return subprocess.Popen(cmd, env=env, cwd=app_dir)

def main():
    print("🚀 Custom Tests Battery - Development Launcher")
    print("=" * 55)
    print("Platform:", "Windows (EXE)" if sys.platform == 'win32' else "macOS (DMG)" if sys.platform == 'darwin' else "Linux")
    print("Mode: Auto-reload development")
    print("Simulating: Executable environment")
    print("=" * 55)
    
    app_process_ref = [None]
    
    # Start initial app
    app_process_ref[0] = start_app()
    print(f"📱 Application started (PID: {app_process_ref[0].pid})")
    
    # Set up file watcher (watch parent directory)
    event_handler = AppReloader(app_process_ref)
    observer = Observer()
    watch_dir = Path(__file__).parent.parent
    observer.schedule(event_handler, str(watch_dir), recursive=True)
    observer.start()
    
    print("👀 Watching for changes... (Press Ctrl+C to stop)")
    print("💡 Edit any .py file to see changes instantly!")
    
    try:
        while True:
            if app_process_ref[0] and app_process_ref[0].poll() is not None:
                print("📱 Application closed")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping development launcher...")
    finally:
        observer.stop()
        observer.join()
        
        if app_process_ref[0] and app_process_ref[0].poll() is None:
            app_process_ref[0].terminate()
            
        print("✅ Development launcher stopped")

if __name__ == "__main__":
    main()