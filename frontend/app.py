import os
from typing import Any

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "210"))

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
            st.session_state.documents = None
            st.rerun()
        else:
            st.error(error_detail(response))


def upload_panel() -> None:
    st.header("Upload evidence")
    st.caption("Index a TXT, LOG, or text-based PDF before starting an investigation.")
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
            st.session_state.documents = None
        else:
            st.error(error_detail(response))

    if st.session_state.get("documents") is None:
        try:
            response = api_request("GET", "/api/documents")
            if response.ok:
                st.session_state.documents = response.json()
        except requests.RequestException:
            st.warning("Document list is temporarily unavailable.")

    documents = st.session_state.get("documents") or []
    if documents:
        st.caption("Indexed documents")
        select_all = st.checkbox(
            "Select all documents",
            help="Select every indexed document for one bulk removal.",
        )
        if select_all and st.button(
            f"Remove all {len(documents)} selected documents",
            type="primary",
            use_container_width=True,
        ):
            try:
                response = api_request("DELETE", "/api/documents")
            except requests.RequestException as exc:
                st.error(f"Bulk removal failed: {exc}")
                return

            if response.ok:
                deleted_count = response.json()["deleted_count"]
                st.session_state.documents = None
                st.session_state.messages = []
                st.success(f"Removed {deleted_count} indexed documents.")
                st.rerun()
            else:
                st.error(error_detail(response))

        for document in documents:
            details, action = st.columns([4, 1])
            details.write(
                f"{document['filename']} ({document['chunk_count']} chunks)"
            )
            if action.button(
                "Remove",
                key=f"remove-{document['id']}",
                use_container_width=True,
            ):
                try:
                    response = api_request(
                        "DELETE",
                        f"/api/documents/{document['id']}",
                    )
                except requests.RequestException as exc:
                    st.error(f"Removal failed: {exc}")
                    return

                if response.ok:
                    st.session_state.documents = None
                    st.success(f"Removed {document['filename']}.")
                    st.rerun()
                else:
                    st.error(error_detail(response))
    else:
        st.info("Upload a document to begin.")


def audit_panel() -> None:
    st.header("Audit activity")
    st.caption("Recent questions and security outcomes for the signed-in analyst.")
    try:
        response = api_request("GET", "/api/audit?limit=100")
    except requests.RequestException as exc:
        st.error(f"Could not load audit records: {exc}")
        return

    if not response.ok:
        st.error(error_detail(response))
        return

    records = response.json()
    if not records:
        st.info("No questions have been audited yet.")
        return

    for record in records:
        files = ", ".join(record["uploaded_files"]) or "No retrieved files"
        st.markdown(f"**{record['question']}**")
        st.caption(
            f"{record['created_at']} | {record['status']} | "
            f"{record['source_count']} sources | {files}"
        )
        if record["response_summary"]:
            st.write(record["response_summary"])
        st.divider()


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

    question = st.chat_input(
        "Ask about the uploaded document, such as: Tell me about yourself"
    )
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
            if response.status_code == 400 and "prompt-injection" in message:
                st.warning(f"Security alert: {message}")
            else:
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
        st.rerun()


def main() -> None:
    if not st.session_state.get("token"):
        login()
        return

    with st.sidebar:
        st.title("SecureAI SOC Copilot")
        st.caption(f"Signed in as {st.session_state.username}")
        page = st.radio("Navigation", ["Upload", "Chat", "Audit"])
        st.divider()
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    if page == "Upload":
        upload_panel()
    elif page == "Audit":
        audit_panel()
    else:
        chat_panel()


if __name__ == "__main__":
    main()
