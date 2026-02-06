from app.core.dto.garvis_dtos import GarvisReply, GarvisTask
from app.database.duckdb_data_service import data_service
from app.services.agentic_assistant_service import AgenticAssistantService

_garvis: "Garvis | None" = None


def get_garvis() -> "Garvis":
    global _garvis

    if _garvis is None:
        AgenticAssistantService.initialize(data_service)

        agent = AgenticAssistantService()
        _garvis = Garvis(agent)

    return _garvis


class Garvis:
    """
    Encapsulates the agent network which ultimately creates Garvis.
    """

    def __init__(self, agent: AgenticAssistantService):
        self.agent = agent

    async def handle_task(self, task: GarvisTask) -> GarvisReply:
        """
        Receives a task that models a user input alongside a distinct session_id.
        Processes this task through Garvis.
        """
        message_from_agent = self.agent.call_agent(task)
        return message_from_agent if self.agent.im_alive else "I'm dead!"
