"""
Configuration Loader and Dynamic Watcher for ClawAgent
"""

import os
import yaml
import logging
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger("clawagent.config")

class ConfigLoader:
    @staticmethod
    def load_yaml(file_path: str) -> Dict[str, Any]:
        """Loads and parses a YAML configuration file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                return data or {}
            except yaml.YAMLError as e:
                logger.error(f"Error parsing YAML from {file_path}: {e}")
                raise

class ConfigWatcher:
    """Optional file watcher for hot-reloading configurations."""
    def __init__(self, file_path: str, on_change_callback: Callable[[Dict[str, Any]], None]):
        self.file_path = os.path.abspath(file_path)
        self.on_change_callback = on_change_callback
        self.observer = None
        self._start_watcher()

    def _start_watcher(self):
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class _Handler(FileSystemEventHandler):
                def __init__(outer_self, target_path, callback):
                    super().__init__()
                    outer_self.target_path = target_path
                    outer_self.callback = callback

                def on_modified(outer_self, event):
                    if os.path.abspath(event.src_path) == outer_self.target_path:
                        try:
                            new_conf = ConfigLoader.load_yaml(outer_self.target_path)
                            outer_self.callback(new_conf)
                            logger.info(f"Hot-reloaded configuration from {outer_self.target_path}")
                        except Exception as ex:
                            logger.error(f"Hot-reload failed: {ex}")

            directory = os.path.dirname(self.file_path)
            self.observer = Observer()
            handler = _Handler(self.file_path, self.on_change_callback)
            self.observer.schedule(handler, directory, recursive=False)
            self.observer.daemon = True
            self.observer.start()
            logger.info(f"Started config file watcher on {self.file_path}")
        except ImportError:
            logger.warning("watchdog library not installed. Hot-reload will be manual or on-access.")
        except Exception as e:
            logger.warning(f"Could not initialize watchdog: {e}")

    def stop(self):
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join()
            except Exception:
                pass
