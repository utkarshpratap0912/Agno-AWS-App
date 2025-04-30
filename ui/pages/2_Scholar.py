import asyncio
import nest_asyncio
import streamlit as st
from agno.agent import Agent
from agno.tools.streamlit.components import check_password
from agno.utils.log import logger

from agents.scholar import get_scholar
from ui.css import CUSTOM_CSS
from ui.utils import (
    about_agno,
    add_message,
    display_tool_calls,
    example_inputs,
    initialize_agent_session_state,
    selected_model,
    session_selector,
    utilities_widget,
)

nest_asyncio.apply()

st.set_page_config(
    page_title="Scholar: The Research Agent",
    page_icon=":crystal_ball:",
    layout="wide",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
agent_name = "scholar"


async def header():
    st.markdown("<h1 class='heading'>Scholar</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subheading'>A research agent that uses DuckDuckGo to deliver in-depth answers about any topic.</p>",
        unsafe_allow_html=True,
    )


async def body() -> None:
    ####################################################################
    # ✅ Get user_id and tenant_id from auth session
    ####################################################################
    if "phantom_token" not in st.session_state:
        st.error("🔐 Please log in first.")
        st.stop()

    tenant_id, username = st.session_state["phantom_token"].split(":")
    st.sidebar.write(f"👤 User: {username}")
    st.sidebar.write(f"🏢 Tenant: {tenant_id}")

    ####################################################################
    # Model selector
    ####################################################################
    model_id = await selected_model()

    ####################################################################
    # Initialize Agent
    ####################################################################
    scholar: Agent
    if (
        agent_name not in st.session_state
        or st.session_state[agent_name]["agent"] is None
        or st.session_state.get("selected_model") != model_id
    ):
        logger.info("---*--- Creating Scholar agent ---*---")
        scholar = get_scholar(user_id=username, tenant_id=tenant_id, username=username, model_id=model_id)
        st.session_state[agent_name] = {
            "agent": scholar,
            "session_id": None,
            "messages": [],
        }
        st.session_state["selected_model"] = model_id
    else:
        scholar = st.session_state[agent_name]["agent"]

    ####################################################################
    # Load Agent Session from the database
    ####################################################################
    try:
        st.session_state[agent_name]["session_id"] = scholar.load_session()
    except Exception:
        st.warning("Could not create Scholar session, is the database running?")
        return

    ####################################################################
    # Load agent runs (chat history)
    ####################################################################
    if scholar.memory:
        agent_runs = scholar.memory.runs
        if len(agent_runs) > 0:
            logger.debug("Loading run history")
            st.session_state[agent_name]["messages"] = []
            for agent_run in agent_runs:
                if agent_run.message is not None:
                    await add_message(agent_name, agent_run.message.role, str(agent_run.message.content))
                if agent_run.response is not None:
                    await add_message(agent_name, "assistant", str(agent_run.response.content), agent_run.response.tools)

    ####################################################################
    # Get user input
    ####################################################################
    if prompt := st.chat_input("✨ What would you like to know, bestie?"):
        await add_message(agent_name, "user", prompt)

    ####################################################################
    # Show example inputs
    ####################################################################
    await example_inputs(agent_name)

    ####################################################################
    # Display agent messages
    ####################################################################
    for message in st.session_state[agent_name]["messages"]:
        if message["role"] in ["user", "assistant"]:
            _content = message["content"]
            if _content is not None:
                with st.chat_message(message["role"]):
                    if "tool_calls" in message and message["tool_calls"]:
                        display_tool_calls(st.empty(), message["tool_calls"])
                    st.markdown(_content)

    ####################################################################
    # Generate response for user message
    ####################################################################
    last_message = st.session_state[agent_name]["messages"][-1] if st.session_state[agent_name]["messages"] else None
    if last_message and last_message.get("role") == "user":
        user_message = last_message["content"]
        logger.info(f"Responding to message: {user_message}")
        with st.chat_message("assistant"):
            tool_calls_container = st.empty()
            resp_container = st.empty()
            with st.spinner(":thinking_face: Thinking..."):
                response = ""
                try:
                    run_response = await scholar.arun(user_message, stream=True)
                    async for resp_chunk in run_response:
                        if resp_chunk.tools and len(resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, resp_chunk.tools)
                        if resp_chunk.content is not None:
                            response += resp_chunk.content
                            resp_container.markdown(response)

                    if scholar.run_response is not None:
                        await add_message(agent_name, "assistant", response, scholar.run_response.tools)
                    else:
                        await add_message(agent_name, "assistant", response)
                except Exception as e:
                    logger.error(f"Error during agent run: {str(e)}", exc_info=True)
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    await add_message(agent_name, "assistant", error_message)
                    st.error(error_message)

    ####################################################################
    # Session selector
    ####################################################################
    await session_selector(agent_name, scholar, get_scholar, username, model_id)

    ####################################################################
    # About section
    ####################################################################
    await utilities_widget(agent_name, scholar)


async def main():
    await initialize_agent_session_state(agent_name)
    await header()
    await body()
    await about_agno()


if __name__ == "__main__":
    if check_password():
        asyncio.run(main())
