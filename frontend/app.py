import os
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = 120

st.set_page_config(
    page_title="SecureAI SOC Copilot",
    layout="wide",
)


def api_request(
    method: str,
    path: str,
    *,
    authenticated: bool = True,
    **kwargs: Any,
) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if authenticated and st.session_state.get("token"):
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    return requests.request(
        method,
        f"{API_BASE_URL}{path}",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )


def error_detail(response: requests.Response) -> str:
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text or f"Request failed with status {response.status_code}"


def login() -> None:
    st.title("SecureAI SOC Copilot")
    st.caption("Grounded answers for cybersecurity logs and reports")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        try:
            response = api_request(
                "POST",
                "/api/auth/token",
                authenticated=False,
                data={"username": username, "password": password},
            )
        except requests.RequestException as exc:
            st.error(f"Could not reach the API: {exc}")
            return

        if response.ok:
            st.session_state.token = response.json()["access_token"]
            st.session_state.username = username
            st.session_state.messages = []
            st.rerun()
        else:
            st.error(error_detail(response))


def upload_panel() -> None:
    st.subheader("Evidence")
    uploaded_file = st.file_uploader(
        "Upload a log or report",
        type=["txt", "log", "pdf"],
        help="Maximum file size is configured by the backend.",
    )
    if uploaded_file and st.button("Index document", use_container_width=True):
        with st.spinner("Extracting and indexing..."):
            try:
                response = api_request(
                    "POST",
                    "/api/documents/upload",
                    files={
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type,
                        )
                    },
                )
            except requests.RequestException as exc:
                st.error(f"Upload failed: {exc}")
                return

        if response.ok:
            document = response.json()["document"]
            st.success(
                f"Indexed {document['filename']} into {document['chunk_count']} chunks."
            )
        else:
            st.error(error_detail(response))

    try:
        response = api_request("GET", "/api/documents")
        if response.ok:
            documents = response.json()
            if documents:
                st.caption("Indexed documents")
                for document in documents:
                    st.write(
                        f"- {document['filename']} ({document['chunk_count']} chunks)"
                    )
            else:
                st.info("Upload a document to begin.")
    except requests.RequestException:
        st.warning("Document list is temporarily unavailable.")


def chat_panel() -> None:
    st.subheader("Investigation chat")
    st.caption(
        "Answers are limited to uploaded evidence. Retrieved excerpts are shown below."
    )

    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for source in message.get("sources", []):
                page = f", page {source['page']}" if source.get("page") else ""
                with st.expander(f"[{source['citation']}] {source['filename']}{page}"):
                    st.write(source["snippet"])

    question = st.chat_input("Ask about indicators, events, users, hosts, or timelines")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching evidence..."):
            try:
                response = api_request(
                    "POST",
                    "/api/chat/ask",
                    json={"question": question},
                )
            except requests.RequestException as exc:
                message = f"Could not reach the API: {exc}"
                st.error(message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": message}
                )
                return

        if not response.ok:
            message = error_detail(response)
            st.error(message)
            st.session_state.messages.append({"role": "assistant", "content": message})
            return

        payload = response.json()
        st.markdown(payload["answer"])
        st.caption(f"Answered by {payload['provider']} / {payload['model']}")
        for source in payload["sources"]:
            page = f", page {source['page']}" if source.get("page") else ""
            with st.expander(f"[{source['citation']}] {source['filename']}{page}"):
                st.write(source["snippet"])
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": payload["answer"],
                "sources": payload["sources"],
            }
        )


def main() -> None:
    if not st.session_state.get("token"):
        login()
        return

    with st.sidebar:
        st.title("SecureAI SOC Copilot")
        st.caption(f"Signed in as {st.session_state.username}")
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.divider()
        upload_panel()

    chat_panel()


if __name__ == "__main__":
    main()
