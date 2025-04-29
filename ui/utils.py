from typing import Any, Callable, Dict, List, Optional
import os
from uuid import UUID
from urllib.parse import urlparse
from datetime import datetime

import streamlit as st
import requests

from agno.agent import Agent
from agno.document import Document
from agno.document.reader import Reader
from agno.document.reader.csv_reader import CSVReader
from agno.document.reader.docx_reader import DocxReader
from agno.document.reader.pdf_reader import PDFReader
from agno.document.reader.text_reader import TextReader
from agno.document.reader.website_reader import WebsiteReader
from agno.utils.log import logger


async def initialize_agent_session_state(agent_name: str):
    logger.info(f"---*--- Initializing session state for {agent_name} ---*---")
    if agent_name not in st.session_state:
        st.session_state[agent_name] = {
            "agent": None,
            "session_id": None,
            "messages": [],
        }


async def selected_model() -> str:
    model_options = {
        "gpt-4o": "gpt-4o",
        "o3-mini": "o3-mini",
    }
    selected_model = st.sidebar.selectbox(
        "Choose a model",
        options=list(model_options.keys()),
        index=0,
        key="model_selector",
    )
    return model_options[selected_model]


async def add_message(
    agent_name: str, role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None
) -> None:
    st.session_state[agent_name]["messages"].append({"role": role, "content": content, "tool_calls": tool_calls})


def display_tool_calls(tool_calls_container, tools):
    if not tools:
        return

    try:
        with tool_calls_container.container():
            for tool_call in tools:
                tool_name = tool_call.get("tool_name", "Unknown Tool")
                tool_args = tool_call.get("tool_args", {})
                content = tool_call.get("content")
                metrics = tool_call.get("metrics", {})
                execution_time_str = "N/A"
                try:
                    if metrics:
                        execution_time = metrics.get("time")
                        if execution_time is not None:
                            execution_time_str = f"{execution_time:.2f}s"
                except Exception as e:
                    logger.error(f"Error displaying tool calls: {str(e)}")

                with st.expander(
                    f"🛠️ {tool_name.replace('_', ' ').title()} ({execution_time_str})",
                    expanded=False,
                ):
                    if isinstance(tool_args, dict) and tool_args.get("query"):
                        st.code(tool_args["query"], language="sql")
                    if tool_args and tool_args != {"query": None}:
                        st.markdown("**Arguments:**")
                        st.json(tool_args)
                    if content:
                        st.markdown("**Results:**")
                        try:
                            if isinstance(content, dict) or (
                                isinstance(content, str) and content.strip().startswith(("{", "["))
                            ):
                                st.json(content)
                            else:
                                st.markdown(content)
                        except Exception:
                            st.markdown(content)
    except Exception as e:
        logger.error(f"Error displaying tool calls: {str(e)}")
        tool_calls_container.error(f"Failed to display tool results: {str(e)}")


async def example_inputs(agent_name: str) -> None:
    with st.sidebar:
        st.markdown("#### 🤔 Try me!")
        if st.button("Who are you?"):
            await add_message(agent_name, "user", "Who are you?")
        if st.button("What is your purpose?"):
            await add_message(agent_name, "user", "What is your purpose?")
        if agent_name == "sage":
            if st.button("Tell me about Agno"):
                await add_message(
                    agent_name,
                    "user",
                    "Tell me about Agno. Github repo: https://github.com/agno-agi/agno. Documentation: https://docs.agno.com",
                )


def process_document_with_agent(agent: Agent, tenant_id: UUID, file_path: str):
    """Uses agent.knowledge.load_documents to auto-vectorize and insert documents."""
    logger.info(f"📄 Loading document for tenant: {tenant_id}")
    file_type = file_path.split(".")[-1].lower()

    reader: Reader
    if file_type == "pdf":
        reader = PDFReader()
    elif file_type == "csv":
        reader = CSVReader()
    elif file_type == "txt":
        reader = TextReader()
    elif file_type == "docx":
        reader = DocxReader()
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    try:
        with open(file_path, "rb") as f:
            documents: List[Document] = reader.read(f)

        if not documents:
            logger.warning(f"No content extracted from: {file_path}")
            return

        agent.knowledge.load_documents(documents, upsert=True, filters={"tenant_id": str(tenant_id)})
        logger.info(f"✅ Document inserted for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"❌ Failed to load document for tenant {tenant_id}: {str(e)}")


async def knowledge_widget(agent_name: str, agent: Agent) -> None:
    tenant_id = st.session_state.get("phantom_token", "").split(":")[0]
    if agent and agent.knowledge:
        if "url_scrape_key" not in st.session_state[agent_name]:
            st.session_state[agent_name]["url_scrape_key"] = 0
        input_url = st.sidebar.text_input(
            "Add URL to Knowledge Base", key=st.session_state[agent_name]["url_scrape_key"]
        )
        if st.sidebar.button("Add URL") and input_url:
            st.sidebar.info("Processing URL...", icon="ℹ️")
            rag_path = os.path.join("rag_data", tenant_id)
            os.makedirs(rag_path, exist_ok=True)
            try:
                response = requests.get(input_url)
                response.raise_for_status()
                parsed_url = urlparse(input_url)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{parsed_url.netloc}_{timestamp}.html"
                file_path = os.path.join(rag_path, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                scraper = WebsiteReader(max_links=2, max_depth=1)
                web_documents: List[Document] = scraper.read(input_url)
                if web_documents:
                    agent.knowledge.load_documents(web_documents, upsert=True, filters={"tenant_id": tenant_id})
                    st.sidebar.success("URL added to knowledge base.")
                else:
                    st.sidebar.error("Could not read website.")
            except Exception as e:
                st.sidebar.error(f"Failed to save URL content: {str(e)}")
            st.session_state[agent_name]["url_scrape_key"] += 1

        if "file_uploader_key" not in st.session_state[agent_name]:
            st.session_state[agent_name]["file_uploader_key"] = 100
        uploaded_file = st.sidebar.file_uploader(
            "Add Document (.pdf, .csv, .txt, .docx)", key=st.session_state[agent_name]["file_uploader_key"],
        )
        if uploaded_file:
            st.sidebar.info("Processing document...", icon="🧠")
            document_name = uploaded_file.name.split(".")[0]
            if f"{document_name}_uploaded" not in st.session_state:
                rag_path = os.path.join("rag_data", tenant_id)
                os.makedirs(rag_path, exist_ok=True)
                file_path = os.path.join(rag_path, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                try:
                    process_document_with_agent(agent, tenant_id, file_path)
                    st.sidebar.success("Document added to knowledge base.")
                except Exception as e:
                    st.sidebar.error(f"Could not process document: {str(e)}")

                st.session_state[f"{document_name}_uploaded"] = True
                st.session_state[agent_name]["file_uploader_key"] += 1

        if st.sidebar.button("🗑️ Delete Knowledge"):
            await agent.knowledge.delete(filters={"tenant_id": tenant_id})
            st.sidebar.success("Knowledge deleted!")


async def session_selector(agent_name: str, agent: Agent, get_agent: Callable, user_id: str, model_id: str) -> None:
    if not agent.storage:
        return
    try:
        agent_sessions = agent.storage.get_all_sessions()
        if not agent_sessions:
            st.sidebar.info("No saved sessions found.")
            return
        sessions_list = []
        for session in agent_sessions:
            session_id = session.session_id
            session_name = session.session_data.get("session_name", None) if session.session_data else None
            display_name = session_name if session_name else session_id
            sessions_list.append({"id": session_id, "display_name": display_name})

        st.sidebar.markdown("#### 💬 Session")
        selected_session = st.sidebar.selectbox(
            "Session",
            options=[s["display_name"] for s in sessions_list],
            key="session_selector",
            label_visibility="collapsed",
        )
        selected_session_id = next(s["id"] for s in sessions_list if s["display_name"] == selected_session)
        if st.session_state[agent_name]["session_id"] != selected_session_id:
            logger.info(f"---*--- Loading {agent_name} session: {selected_session_id} ---*---")
            st.session_state[agent_name]["agent"] = get_agent(
                user_id=user_id,
                model_id=model_id,
                session_id=selected_session_id,
            )
            st.rerun()

        container = st.sidebar.container()
        session_row = container.columns([3, 1], vertical_alignment="center")
        if "session_edit_mode" not in st.session_state:
            st.session_state.session_edit_mode = False
        with session_row[0]:
            if st.session_state.session_edit_mode:
                new_session_name = st.text_input(
                    "Session Name",
                    value=agent.session_name,
                    key="session_name_input",
                    label_visibility="collapsed",
                )
            else:
                st.markdown(f"Session Name: **{agent.session_name}**")
        with session_row[1]:
            if st.session_state.session_edit_mode:
                if st.button("✓", key="save_session_name", type="primary"):
                    if new_session_name:
                        agent.rename_session(new_session_name)
                        st.session_state.session_edit_mode = False
                        container.success("Renamed!")
                        st.rerun()
            else:
                if st.button("✎", key="edit_session_name"):
                    st.session_state.session_edit_mode = True
    except Exception as e:
        logger.error(f"Error in session selector: {str(e)}")
        st.sidebar.error("Failed to load sessions")


def export_chat_history(agent_name: str):
    if "messages" not in st.session_state[agent_name] or not st.session_state[agent_name]["messages"]:
        return f"# {agent_name} - Chat History\n\nNo messages to export."
    chat_text = f"# {agent_name} - Chat History\n\n"
    for msg in st.session_state[agent_name]["messages"]:
        role_label = "🤖 Assistant" if msg["role"] == "assistant" else "👤 User"
        chat_text += f"### {role_label}\n{msg['content']}\n\n"
        if msg.get("tool_calls"):
            chat_text += "#### Tool Calls:\n"
            for i, tool_call in enumerate(msg["tool_calls"]):
                tool_name = tool_call.get("name", "Unknown Tool")
                chat_text += f"**{i + 1}. {tool_name}**\n\n"
                if "arguments" in tool_call:
                    chat_text += f"Arguments: ```json\n{tool_call['arguments']}\n```\n\n"
                if "content" in tool_call:
                    chat_text += f"Results: ```\n{tool_call['content']}\n```\n\n"
    return chat_text


async def utilities_widget(agent_name: str, agent: Agent) -> None:
    st.sidebar.markdown("#### 🛠️ Utilities")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Start New Chat"):
            restart_agent(agent_name)
    with col2:
        fn = f"{agent_name}_chat_history.md"
        if "session_id" in st.session_state[agent_name]:
            fn = f"{agent_name}_{st.session_state[agent_name]['session_id']}.md"
        if st.download_button(
            ":file_folder: Export Chat History",
            export_chat_history(agent_name),
            file_name=fn,
            mime="text/markdown",
        ):
            st.sidebar.success("Chat history exported!")


def restart_agent(agent_name: str):
    logger.debug("---*--- Restarting Agent ---*---")
    st.session_state[agent_name]["agent"] = None
    st.session_state[agent_name]["session_id"] = None
    st.session_state[agent_name]["messages"] = []
    if "url_scrape_key" in st.session_state[agent_name]:
        st.session_state[agent_name]["url_scrape_key"] += 1
    if "file_uploader_key" in st.session_state[agent_name]:
        st.session_state[agent_name]["file_uploader_key"] += 1
    st.rerun()


async def about_agno():
    with st.sidebar:
        st.markdown("### About Agno ✨")
        st.markdown("""
        Agno is an open-source library for building Multimodal Agents.

        [GitHub](https://github.com/agno-agi/agno) | [Docs](https://docs.agno.com)
        """)
        st.markdown("### Need Help?")
        st.markdown(
            "If you have any questions, catch us on [discord](https://agno.link/discord) or post in the community [forum](https://agno.link/community)."
        )


async def footer():
    st.markdown("---")
    st.markdown(
        "<p style='text-align: right; color: gray;'>Built using <a href='https://github.com/agno-agi/agno'>Agno</a></p>",
        unsafe_allow_html=True,
    )
