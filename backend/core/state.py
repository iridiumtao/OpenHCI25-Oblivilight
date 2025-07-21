from typing import Optional, List


class SystemState:
    """
    Manages the global state of the backend application.
    This class is intended to be a singleton.
    """

    def __init__(self):
        self.is_listening: bool = False
        self.is_processing: bool = False  # Lock for tasks like forgetting or summarizing
        self.is_forgetting: bool = False
        self.injected_context: Optional[str] = None
        self.conversation_history: List[str] = []
        self.full_audio_path: Optional[str] = None

    def reset_session(self):
        """Resets the state for a new user session."""
        self.is_listening = False
        self.is_processing = False
        self.is_forgetting = False
        self.injected_context = None
        self.conversation_history = []
        self.full_audio_path = None
        print("System state has been reset for a new session.")


# Singleton instance
system_state = SystemState() 