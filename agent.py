"""
Policy Debate Simulator
=======================
Pattern : Hierarchical Multi-Agent — adversarial (ConnectedAgentTool)

Three specialist agents are wired together under a conductor:
  - proponent_agent : argues FOR the policy
  - opponent_agent  : argues AGAINST the policy
  - judge_agent     : scores both sides and delivers a verdict

The conductor receives a policy statement, calls each specialist in sequence
via ConnectedAgentTool, and assembles the full debate transcript.

SDK used: azure-ai-agents (AgentsClient + threads/runs model)
This is distinct from Projects 01-03 which used azure-ai-projects +
the Responses API. AgentsClient uses the Assistants-style thread/run pattern:
  - agents_client.threads.create()        : create a conversation thread
  - agents_client.messages.create()       : add a message to the thread
  - agents_client.runs.create_and_process(): run the agent to completion
  - agents_client.messages.list()         : retrieve the response
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole, ListSortOrder


# ---------------------------------------------------------------------------
# Load prompt from file
# ---------------------------------------------------------------------------
def load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).parent / "prompts" / filename
    return prompt_path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def print_banner():
    print("=" * 60)
    print("   POLICY DEBATE SIMULATOR")
    print("   Powered by Azure AI Foundry — Multi-Agent (Connected)")
    print("=" * 60)
    print()


def get_last_assistant_message(messages) -> str:
    """Extract the final assistant text from a thread message list."""
    for message in reversed(list(messages)):
        if message.role == MessageRole.AGENT and message.text_messages:
            return message.text_messages[-1].text.value
    return "[No response received]"


def print_sample_policies():
    print("Sample policy statements to debate:")
    print("  - Governments should ban single-use plastics entirely.")
    print("  - University education should be free for all citizens.")
    print("  - Social media platforms should be regulated as public utilities.")
    print("  - Autonomous vehicles should be permitted on all public roads.")
    print("  - Remote work should be a legal right for all office workers.")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print_banner()

    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not project_endpoint or not model_deployment:
        print("ERROR: PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME must be set in .env")
        sys.exit(1)

    # Load all prompts up front
    proponent_instructions = load_prompt("proponent_prompt.txt")
    opponent_instructions  = load_prompt("opponent_prompt.txt")
    judge_instructions     = load_prompt("judge_prompt.txt")
    conductor_instructions = load_prompt("conductor_prompt.txt")

    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )

    with AgentsClient(endpoint=project_endpoint, credential=credential) as agents_client:

        # -- Create the three specialist agents -------------------------------
        print("Creating specialist agents...")

        proponent_agent = agents_client.create_agent(
            model=model_deployment,
            name="proponent_agent",
            instructions=proponent_instructions,
        )
        print(f"  Proponent agent: {proponent_agent.id}")

        opponent_agent = agents_client.create_agent(
            model=model_deployment,
            name="opponent_agent",
            instructions=opponent_instructions,
        )
        print(f"  Opponent agent:  {opponent_agent.id}")

        judge_agent = agents_client.create_agent(
            model=model_deployment,
            name="judge_agent",
            instructions=judge_instructions,
        )
        print(f"  Judge agent:     {judge_agent.id}\n")

        # -- Wrap each specialist as a ConnectedAgentTool ---------------------
        proponent_tool = ConnectedAgentTool(
            id=proponent_agent.id,
            name="proponent_agent",
            description="Argues in favour of the policy statement with structured evidence-based reasoning.",
        )
        opponent_tool = ConnectedAgentTool(
            id=opponent_agent.id,
            name="opponent_agent",
            description="Argues against the policy statement with structured evidence-based reasoning.",
        )
        judge_tool = ConnectedAgentTool(
            id=judge_agent.id,
            name="judge_agent",
            description=(
                "Scores both the proponent and opponent arguments on logic, evidence, "
                "and persuasion, then delivers a verdict."
            ),
        )

        # -- Create the conductor agent with all three tools ------------------
        conductor_agent = agents_client.create_agent(
            model=model_deployment,
            name="debate_conductor",
            instructions=conductor_instructions,
            tools=[
                proponent_tool.definitions[0],
                opponent_tool.definitions[0],
                judge_tool.definitions[0],
            ],
        )
        print(f"Conductor agent ready: {conductor_agent.id}\n")

        # -- Debate loop ------------------------------------------------------
        print_sample_policies()

        while True:
            try:
                policy = input("Enter a policy statement to debate (or 'quit' to exit):\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

            if policy.lower() in ("quit", "exit", "q"):
                break
            if not policy:
                print("Please enter a policy statement.\n")
                continue

            print(f"\nDebate starting on: \"{policy}\"")
            print("Consulting agents — this may take a moment...\n")

            # Create a fresh thread for each debate
            thread = agents_client.threads.create()

            agents_client.messages.create(
                thread_id=thread.id,
                role=MessageRole.USER,
                content=policy,
            )

            run = agents_client.runs.create_and_process(
                thread_id=thread.id,
                agent_id=conductor_agent.id,
            )

            if run.status == "failed":
                print(f"[Error] Run failed: {run.last_error}\n")
                continue

            messages = agents_client.messages.list(
                thread_id=thread.id,
                order=ListSortOrder.ASCENDING,
            )

            debate_output = get_last_assistant_message(messages)
            print(debate_output)
            print()

            again = input("Debate another policy? (yes / no): ").strip().lower()
            if again not in ("yes", "y"):
                break
            print()

        # -- Cleanup ----------------------------------------------------------
        print("\nCleaning up agents...")
        for agent, label in [
            (conductor_agent, "Conductor"),
            (proponent_agent, "Proponent"),
            (opponent_agent,  "Opponent"),
            (judge_agent,     "Judge"),
        ]:
            try:
                agents_client.delete_agent(agent.id)
                print(f"  {label} agent deleted.")
            except Exception as e:
                print(f"  Warning: could not delete {label} agent — {e}")

        print("\nSession complete.")


if __name__ == "__main__":
    main()
