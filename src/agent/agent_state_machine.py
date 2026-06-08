"""Agent State Machine managing review lifecycle states."""
import logging
from enum import Enum, auto

logger = logging.getLogger("ReviewEngine.Agent")

class AgentState(Enum):
    """Supported execution states in the review lifecycle."""
    INITIALIZED = auto()
    OBSERVING = auto()
    ANALYZING = auto()
    VALIDATING = auto()
    PRIORITIZING = auto()
    ACTING = auto()
    REPORTING = auto()
    COMPLETED = auto()
    FAILED = auto()


class AgentStateMachine:
    """Manages review lifecycle transitions and validates state rules."""

    def __init__(self) -> None:
        self.current_state = AgentState.INITIALIZED
        
        # Valid state transitions lookup map
        self._transitions = {
            AgentState.INITIALIZED: {AgentState.OBSERVING, AgentState.FAILED},
            AgentState.OBSERVING: {AgentState.ANALYZING, AgentState.REPORTING, AgentState.FAILED},
            AgentState.ANALYZING: {AgentState.VALIDATING, AgentState.PRIORITIZING, AgentState.FAILED},
            AgentState.VALIDATING: {AgentState.PRIORITIZING, AgentState.REPORTING, AgentState.FAILED},
            AgentState.PRIORITIZING: {AgentState.ACTING, AgentState.FAILED},
            AgentState.ACTING: {AgentState.REPORTING, AgentState.FAILED},
            AgentState.REPORTING: {AgentState.COMPLETED, AgentState.FAILED},
            AgentState.COMPLETED: set(),  # Terminal state
            AgentState.FAILED: {AgentState.REPORTING, AgentState.COMPLETED} # Allows error reports
        }

    def transition_to(self, target_state: AgentState) -> None:
        """Transitions the agent to the target state.

        Args:
            target_state: The target AgentState.

        Raises:
            ValueError: If the state transition is invalid.
        """
        if target_state == self.current_state:
            return

        allowed_targets = self._transitions.get(self.current_state, set())
        
        if target_state not in allowed_targets:
            # Prevent invalid state jumps
            err_msg = f"Invalid state transition: cannot jump from {self.current_state.name} to {target_state.name}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        logger.info(
            f"State Transition: {self.current_state.name} -> {target_state.name}",
            extra={"context": {"from": self.current_state.name, "to": target_state.name}}
        )
        self.current_state = target_state
