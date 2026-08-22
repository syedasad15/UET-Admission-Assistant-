import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(r"D:\UET Chatbot")

RETRIEVAL_DIR = (
    PROJECT_ROOT
    / "app"
    / "retrieval"
)

VECTORSTORE_DIR = (
    PROJECT_ROOT
    / "data"
    / "vectorstore"
    / "chroma"
)

ENV_FILE = (
    RETRIEVAL_DIR
    / "keyy.env"
)


# ============================================================
# MAKE retrieval.py IMPORTABLE
# ============================================================

if str(RETRIEVAL_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(RETRIEVAL_DIR)
    )


# ============================================================
# IMPORT PRODUCTION RETRIEVER
# ============================================================

try:

    from retrieval import (
        route_question,
        load_collection,
        load_embedding_model,
    )

except Exception as import_error:

    st.error(
        "Could not load the production retrieval system."
    )

    st.code(
        str(import_error)
    )

    st.stop()


# ============================================================
# CONFIGURATION
# ============================================================

EMBEDDING_MODEL_NAME = (
    "BAAI/bge-small-en-v1.5"
)

COLLECTION_NAME = (
    "uet_admission_knowledge"
)

GEMINI_MODEL = (
    "gemini-3.6-flash"
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="UET Admissions Chatbot",
    page_icon="🎓",
    layout="centered",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        text-align: center;
        color: #777;
        margin-bottom: 2rem;
    }

    .merit-card {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.8rem;
        background-color: rgba(128,128,128,0.08);
        border-left: 4px solid #4F8BF9;
    }

    .success-card {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.8rem;
        background-color: rgba(0,180,80,0.10);
        border-left: 4px solid #00A651;
    }

    .warning-card {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.8rem;
        background-color: rgba(255,165,0,0.10);
        border-left: 4px solid #F39C12;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🎓 UET Admissions Chatbot</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Ask questions about UET admissions, programs, fees, "
    "eligibility, deadlines, scholarships and merit."
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv(
    ENV_FILE,
    override=False,
)

API_KEY = os.getenv(
    "GOOGLE_API_KEY"
)

if not API_KEY:

    API_KEY = os.getenv(
        "GEMINI_API_KEY"
    )


# ============================================================
# GEMINI
# ============================================================

@st.cache_resource
def load_gemini():

    if not API_KEY:
        return None

    return genai.Client(
        api_key=API_KEY
    )


# ============================================================
# CHROMA + EMBEDDING MODEL
# ============================================================

@st.cache_resource
def get_collection():

    return load_collection()


@st.cache_resource
def get_embedding_model():

    return load_embedding_model()


# ============================================================
# GENERATE NORMAL ANSWER
# ============================================================

def generate_answer(
    question,
    results,
    client,
):

    if not results:

        return (
            "I couldn't find sufficiently relevant "
            "information in the UET admissions knowledge base "
            "for this question."
        )

    if client is None:

        return (
            "I found relevant UET admissions information, "
            "but the Gemini API key is not configured."
        )

    context_parts = []

    for index, result in enumerate(
        results,
        start=1,
    ):

        source_type = result.get(
            "source_type",
            "",
        )

        title = result.get(
            "title",
            "",
        )

        url = result.get(
            "url",
            "",
        )

        pdf_file = result.get(
            "pdf_file",
            "",
        )

        page = result.get(
            "page",
            None,
        )

        text = result.get(
            "text",
            "",
        )

        context_parts.append(
            f"""
Source #{index}
Title: {title}
Source type: {source_type}
PDF file: {pdf_file}
Page: {page}
URL: {url}

Content:
{text}
"""
        )

    context = "\n\n".join(
        context_parts
    )

    prompt = f"""
You are the official-style UET Admissions Chatbot.

Answer the user's question using ONLY the retrieved
UET admissions evidence below.

Rules:

1. Give the direct answer first.
2. Do not invent facts.
3. If the evidence is insufficient, clearly say so.
4. Preserve important numbers exactly.
5. If asked "how many", provide the count.
6. If programs are listed, provide the relevant program names.
7. Do not mention ChromaDB, embeddings, vector databases,
   retrieval pipelines, or internal implementation.
8. Do not fabricate sources.
9. Keep the answer concise but useful.

User question:
{question}

Retrieved UET evidence:
{context}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    if not response.text:

        return (
            "I was unable to generate an answer from "
            "the available UET information."
        )

    return response.text


# ============================================================
# DISPLAY NORMAL SOURCES
# ============================================================

def display_sources(
    results
):

    if not results:
        return

    with st.expander(
        f"📚 Sources ({len(results)})"
    ):

        for index, result in enumerate(
            results,
            start=1,
        ):

            source_type = result.get(
                "source_type",
                "",
            )

            title = result.get(
                "title",
                "Unknown source",
            )

            url = result.get(
                "url",
                "",
            )

            page = result.get(
                "page",
                None,
            )

            pdf_file = result.get(
                "pdf_file",
                "",
            )

            st.markdown(
                f"**{index}. {title}**"
            )

            if source_type == "pdf":

                if pdf_file:

                    if page:

                        st.caption(
                            f"PDF: {pdf_file} | "
                            f"Page: {page}"
                        )

                    else:

                        st.caption(
                            f"PDF: {pdf_file}"
                        )

            else:

                st.caption(
                    "Official UET admissions webpage"
                )

            if url:

                st.markdown(
                    f"[🔗 Open source]({url})"
                )

            st.divider()


# ============================================================
# DISPLAY MERIT RESPONSE
# ============================================================

def display_merit_response(
    response
):

    if not response:

        st.error(
            "No merit response was returned."
        )

        return

    message = response.get(
        "message",
        "",
    )

    source_url = response.get(
        "source_url",
        "",
    )

    records = response.get(
        "records",
        [],
    )

    response_type = response.get(
        "type",
        "merit",
    )

    success = response.get(
        "success",
        False,
    )

    # --------------------------------------------------------
    # No records
    # --------------------------------------------------------

    if not success or not records:

        st.warning(
            message
            or
            "No matching current merit record was found."
        )

        if source_url:

            st.markdown(
                f"[🔗 Open UET merit source]({source_url})"
            )

        return

    # --------------------------------------------------------
    # Merit check
    # --------------------------------------------------------

    if response_type == "merit_check":

        student_aggregate = response.get(
            "student_aggregate"
        )

        st.markdown(
            f"### 🎯 Merit Check"
        )

        if student_aggregate is not None:

            st.info(
                f"Your aggregate: **{student_aggregate:.5f}**"
            )

    else:

        st.markdown(
            "### 📊 Current UET Merit"
        )

    # --------------------------------------------------------
    # Records
    # --------------------------------------------------------

    for record in records:

        campus = record.get(
            "campus",
            "Unknown",
        )

        program = record.get(
            "program",
            "Unknown",
        )

        category = record.get(
            "category",
            "Unknown",
        )

        session = record.get(
            "session",
            "Unknown",
        )

        merit_type = record.get(
            "type",
            "Unknown",
        )

        minimum = record.get(
            "minimum_aggregate"
        )

        page = record.get(
            "page"
        )

        # ----------------------------------------------------
        # Merit check result
        # ----------------------------------------------------

        if (
            "selected"
            in record
        ):

            selected = record.get(
                "selected",
                False,
            )

            difference = record.get(
                "difference",
                0,
            )

            if selected:

                st.markdown(
                    f"""
                    <div class="success-card">

                    <h4>✅ SELECTED / ABOVE CURRENT MERIT</h4>

                    <b>Campus:</b> {campus}<br>
                    <b>Program:</b> {program}<br>
                    <b>Category:</b> {category}<br>
                    <b>Session:</b> {session}<br>
                    <b>Minimum Merit:</b> {minimum:.5f}<br>
                    <b>Your Aggregate:</b> {record.get("student_aggregate", 0):.5f}<br>
                    <b>Difference:</b> +{difference:.5f}

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    f"""
                    <div class="warning-card">

                    <h4>❌ BELOW CURRENT MERIT</h4>

                    <b>Campus:</b> {campus}<br>
                    <b>Program:</b> {program}<br>
                    <b>Category:</b> {category}<br>
                    <b>Session:</b> {session}<br>
                    <b>Minimum Merit:</b> {minimum:.5f}<br>
                    <b>Your Aggregate:</b> {record.get("student_aggregate", 0):.5f}<br>
                    <b>Difference:</b> {difference:.5f}

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # ----------------------------------------------------
        # Normal merit lookup
        # ----------------------------------------------------

        else:

            st.markdown(
                f"""
                <div class="merit-card">

                <b>Campus:</b> {campus}<br>
                <b>Program:</b> {program}<br>
                <b>Category:</b> {category}<br>
                <b>Session:</b> {session}<br>
                <b>Type:</b> {merit_type}<br>
                <b>Minimum Merit:</b> {minimum:.5f}

                </div>
                """,
                unsafe_allow_html=True,
            )

        if page:

            st.caption(
                f"PDF Page: {page}"
            )

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    if source_url:

        st.markdown(
            f"[🔗 Open official UET merit source]({source_url})"
        )


# ============================================================
# MERIT ERROR HANDLER
# ============================================================

def display_merit_error(
    error
):

    error_text = str(
        error
    )

    # --------------------------------------------------------
    # Known merit website/PDF issue
    # --------------------------------------------------------

    if (
        "did not expose any merit-list PDF links"
        in error_text
    ):

        st.warning(
            "⚠️ The latest UET merit list could not be "
            "retrieved from the UET website right now."
        )

        st.info(
            "Your question was correctly detected as a "
            "merit question, but the current merit source "
            "is unavailable. I will not guess whether you "
            "are selected."
        )

        with st.expander(
            "Technical details"
        ):

            st.code(
                error_text
            )

        return

    # --------------------------------------------------------
    # Other merit errors
    # --------------------------------------------------------

    st.error(
        "The merit system could not process this question."
    )

    with st.expander(
        "Technical details"
    ):

        st.code(
            error_text
        )


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:

    st.session_state.messages = []


# ============================================================
# SHOW CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )

        if (
            message["role"]
            == "assistant"
        ):

            if message.get(
                "route"
            ) == "merit":

                merit_response = message.get(
                    "merit_response"
                )

                if merit_response:

                    display_merit_response(
                        merit_response
                    )

            elif message.get(
                "sources"
            ):

                display_sources(
                    message["sources"]
                )


# ============================================================
# CHAT INPUT
# ============================================================

question = st.chat_input(
    "Ask about UET admissions..."
)


if question:

    # ========================================================
    # USER MESSAGE
    # ========================================================

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message(
        "user"
    ):

        st.markdown(
            question
        )

    # ========================================================
    # ASSISTANT
    # ========================================================

    with st.chat_message(
        "assistant"
    ):

        try:

            # ------------------------------------------------
            # Load retrieval system
            # ------------------------------------------------

            with st.spinner(
                "Processing your question..."
            ):

                collection = (
                    get_collection()
                )

                embedding_model = (
                    get_embedding_model()
                )

                # IMPORTANT:
                # This is now the production router
                # from retrieval.py.
                routed_result = (
                    route_question(
                        question,
                        collection,
                        embedding_model,
                    )
                )

            route = routed_result.get(
                "route"
            )

            # =================================================
            # MERIT ROUTE
            # =================================================

            if route == "merit":

                merit_response = (
                    routed_result.get(
                        "response",
                        {},
                    )
                )

                display_merit_response(
                    merit_response
                )

                # Save a simple chat message.
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            merit_response.get(
                                "message",
                                "Merit result generated."
                            )
                        ),
                        "route": "merit",
                        "merit_response":
                            merit_response,
                    }
                )

            # =================================================
            # NORMAL SEMANTIC ROUTE
            # =================================================

            elif route == "semantic":

                results = routed_result.get(
                    "results",
                    [],
                )

                confidence = routed_result.get(
                    "confidence",
                    "none",
                )

                with st.spinner(
                    "Preparing answer..."
                ):

                    client = (
                        load_gemini()
                    )

                    answer = generate_answer(
                        question,
                        results,
                        client,
                    )

                st.markdown(
                    answer
                )

                if results:

                    display_sources(
                        results
                    )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "route": "semantic",
                        "sources": results,
                        "confidence": confidence,
                    }
                )

            # =================================================
            # UNKNOWN ROUTE
            # =================================================

            else:

                st.error(
                    "The retrieval system returned "
                    "an unknown route."
                )

                st.code(
                    str(routed_result)
                )

        except RuntimeError as error:

            # =================================================
            # IMPORTANT:
            # Merit.py can throw RuntimeError when UET does
            # not expose the latest PDF.
            #
            # Do NOT show a huge Streamlit traceback.
            # =================================================

            if (
                "merit"
                in str(error).lower()
                or
                "merit-list PDF"
                in str(error)
            ):

                display_merit_error(
                    error
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "The latest UET merit source "
                            "is currently unavailable."
                        ),
                        "route": "merit_error",
                    }
                )

            else:

                st.error(
                    "Something went wrong while "
                    "processing your question."
                )

                with st.expander(
                    "Technical details"
                ):

                    st.exception(
                        error
                    )

        except Exception as error:

            st.error(
                "Something went wrong while "
                "processing your question."
            )

            with st.expander(
                "Technical details"
            ):

                st.exception(
                    error
                )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "About"
    )

    st.write(
        "This chatbot answers UET admissions questions "
        "using the university admissions knowledge base."
    )

    st.divider()

    st.subheader(
        "Routing"
    )

    st.write(
        "🎯 Merit questions → latest UET merit data"
    )

    st.write(
        "📚 Normal questions → ChromaDB semantic search"
    )

    st.divider()

    st.write(
        f"Embedding model: "
        f"`{EMBEDDING_MODEL_NAME}`"
    )

    st.write(
        f"LLM: `{GEMINI_MODEL}`"
    )

    st.write(
        f"Vector DB: `{COLLECTION_NAME}`"
    )

    st.divider()

    if st.button(
        "🗑️ Clear chat"
    ):

        st.session_state.messages = []

        st.rerun()