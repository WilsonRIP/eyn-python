from __future__ import annotations

import time
from typing import Optional, Callable, Dict, Any
from pathlib import Path

from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
    SpinnerColumn,
    TaskID,
)
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from eyn_python.logging import console

# Global console instance
_console = console()


class DownloadProgress:
    """A progress bar for file downloads with Rich."""
    
    def __init__(self, filename: str, total_size: Optional[int] = None):
        self.filename = filename
        self.total_size = total_size
        self.start_time = time.time()
        self.downloaded = 0
        
        # Create progress display
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=_console,
            transient=True,
        )
        
        # Create the task
        self.task_id = self.progress.add_task(
            f"Downloading {filename}",
            total=total_size if total_size else None,
            filename=filename
        )
        
    def update(self, chunk_size: int) -> None:
        """Update progress with downloaded chunk size."""
        self.downloaded += chunk_size
        self.progress.update(self.task_id, completed=self.downloaded)
        
    def set_total(self, total_size: int) -> None:
        """Set the total file size if not known initially."""
        self.total_size = total_size
        self.progress.update(self.task_id, total=total_size)
        
    def finish(self) -> None:
        """Mark download as complete."""
        if self.total_size:
            self.progress.update(self.task_id, completed=self.total_size)
        self.progress.stop()
        
    def __enter__(self):
        self.progress.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()


class YouTubeProgressHook:
    """Progress hook for YouTube downloads using Rich progress bars."""
    
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=_console,
            transient=True,
        )
        self.tasks: Dict[str, TaskID] = {}
        self.progress.start()
        
    def __call__(self, d: Dict[str, Any]) -> None:
        """Progress hook callback for yt-dlp."""
        status = d.get("status")
        
        if status == "downloading":
            filename = d.get("filename", "Unknown")
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            speed = d.get("speed", 0)
            eta = d.get("eta")
            
            # Create or update task
            if filename not in self.tasks:
                task_id: TaskID = self.progress.add_task(
                    f"Downloading {Path(filename).name}",
                    total=total,
                    filename=filename
                )
                self.tasks[filename] = task_id
            else:
                task_id = self.tasks[filename]
                
            # Update progress
            self.progress.update(task_id, completed=downloaded)
            
        elif status == "finished":
            filename = d.get("filename", "Unknown")
            if filename in self.tasks:
                task_id = self.tasks[filename]
                self.progress.update(task_id, description=f"[green]✓ Downloaded {Path(filename).name}")
                
        elif status == "error":
            filename = d.get("filename", "Unknown")
            if filename in self.tasks:
                task_id = self.tasks[filename]
                self.progress.update(task_id, description=f"[red]✗ Error downloading {Path(filename).name}")
                
    def stop(self) -> None:
        """Stop the progress display."""
        self.progress.stop()


def create_youtube_progress_hook() -> Callable[[Dict[str, Any]], None]:
    """Factory function to create a YouTube progress hook."""
    hook = YouTubeProgressHook()
    return hook


def download_with_progress(
    url: str,
    output_path: Path,
    filename: str,
    total_size: Optional[int] = None,
    chunk_size: int = 8192
) -> None:
    """
    Download a file with progress bar using httpx.
    
    Args:
        url: URL to download from
        output_path: Path where file should be saved
        filename: Name of the file for display
        total_size: Total file size if known
        chunk_size: Size of chunks to download
    """
    import httpx
    
    with DownloadProgress(filename, total_size) as progress:
        with httpx.stream("GET", url, follow_redirects=True, timeout=30.0) as response:
            response.raise_for_status()
            
            # Update total size if not provided
            if not total_size and "content-length" in response.headers:
                total_size = int(response.headers["content-length"])
                progress.set_total(total_size)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with progress
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    f.write(chunk)
                    progress.update(len(chunk))
                    
        progress.finish()


def format_file_size(size_bytes: float) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
        
    return f"{size_bytes:.1f}{size_names[i]}"


def format_speed(speed_bytes_per_sec: float) -> str:
    """Format speed in human readable format."""
    return format_file_size(speed_bytes_per_sec) + "/s"
