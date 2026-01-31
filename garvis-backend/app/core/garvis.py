from app.core.garvis_task import GarvisTask
from app.database.duckdb_data_service import DataService
from app.services.agentic_assistant_service import AgenticAssistantService


def get_garvis() -> "Garvis":
    ds = DataService()
    AgenticAssistantService.initialize(ds)

    agent = AgenticAssistantService()
    garvis = Garvis(agent)

    return garvis


class Garvis:
    """
    Encapsulates the agent network which ultimately creates Garvis.
    """

    def __init__(self, agent: AgenticAssistantService):
        self.agent = agent

    async def handle_task(self, task: GarvisTask):
        """
        Receives a task that models a user input alongside a distinct session_id.
        Processes this task through Garvis.
        """
        message_from_agent = self.agent.call_agent(task)
        return message_from_agent if self.agent.im_alive else "I'm dead!"
