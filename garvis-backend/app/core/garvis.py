from app.core.garvis_task import GarvisTask
from app.services.agentic_assistant_service import AgenticAssistantService

class Garvis:
    """
    #TODO: Brando, this is where you hook into your agent network to process handle_task.
    The class encapsulating the agent network which ultimately create Garvis.
    """

    def __init__(self, agent: AgenticAssistantService):
        self.agent = agent
        pass

    async def handle_task(self, task: GarvisTask):
        """
        Receives a task that models a user input alongside a distinct session_id.
        Process this task through Garvis and return a still yet to be modelled return.
        """
        
        message_from_agent = self.agent.call_agent(task)
        return message_from_agent if self.agent.im_alive else "Im dead!"
