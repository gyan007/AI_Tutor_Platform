import streamlit as st
import tempfile
import json
import pandas as pd
import altair as alt
import uuid

from ai_tutor_platform.modules.tutor.chat_tutor import ask_tutor
from ai_tutor_platform.modules.doubt_solver.file_handler import solve_doubt_from_file
from ai_tutor_platform.modules.quiz.quiz_generator import generate_quiz
from ai_tutor_platform.db.mongo_client import (
    save_chat, save_file_doubt, save_quiz_response, save_user_progress, get_user_progress
)

st.set_page_config(page_title="AI Tutor Platform", layout="wide")

# -----------------------------
# Session state initialization
# -----------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "score_history" not in st.session_state:
    st.session_state.score_history = []
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

st.title("\U0001F393 AI Tutor Platform")
st.caption("Powered by Mistral 7B via LM Studio")

# ------------------
# Tabs Declaration
# ------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "\U0001F4AC Chat Tutor",
    "\U0001F4C1 Doubt from File",
    "\U0001F4DD Quiz Generator",
    "\U0001F4CA Progress Tracker"
])

# ----------------------------
# ✨ Tab 1: Chat Tutor
# ----------------------------
with tab1:
    st.subheader("Chat with your AI Tutor")
    user_input = st.text_input("Ask something:", key="chat_input")

    if st.button("Send", key="send_chat"):
        if user_input.strip():
            with st.spinner("Thinking..."):
                response = ask_tutor(user_input)
                st.session_state.chat_history.append(("user", user_input))
                st.session_state.chat_history.append(("ai", response))
                save_chat(st.session_state.user_id, user_input, response)
        else:
            st.warning("Please enter a question.")

    if st.session_state.chat_history:
        st.markdown("#### Conversation History")
        for role, msg in st.session_state.chat_history:
            if role == "user":
                st.markdown(f"**\U0001F9D1 You:** {msg}")
            else:
                st.markdown(f"**\U0001F916 AI:** {msg}")

    if st.button("Clear Chat"):
        st.session_state.chat_history = []

# ----------------------------
# 📁 Tab 2: Doubt Solver from File
# ----------------------------
with tab2:
    st.subheader("Upload File and Ask a Question")
    uploaded_file = st.file_uploader("Choose file (PDF, TXT, JPG, PNG)", type=["pdf", "txt", "jpg", "jpeg", "png"])
    file_question = st.text_input("What is your question about this file?", key="file_q")

    if st.button("Solve Doubt"):
        if uploaded_file and file_question.strip():
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name

            with st.spinner("Processing file..."):
                answer = solve_doubt_from_file(tmp_file_path, file_question)
            st.success("Answer:")
            st.write(answer)
            save_file_doubt(st.session_state.user_id, uploaded_file.name, file_question, answer)
        else:
            st.warning("Please upload a file and enter a question.")

# ----------------------------
# 📝 Tab 3: Quiz Generator
# ----------------------------
with tab3:
    st.subheader("\U0001F9E0 Generate a Subject Quiz")

    subject = st.selectbox("Select a subject:", ["Math", "Science", "History", "Geography", "English"])
    num_questions = st.slider("Number of questions:", min_value=1, max_value=10, value=3)

    if st.button("Generate Quiz"):
        with st.spinner("Generating quiz..."):
            quiz = generate_quiz(subject, num_questions)

            if "ERROR" in quiz[0].get("question", ""):
                st.error(quiz[0]["question"])
                st.session_state.quiz_questions = []
                st.session_state.quiz_submitted = False
            else:
                st.session_state.quiz_questions = quiz
                st.session_state.quiz_submitted = False

            st.markdown("#### 🛠️ Raw Quiz Output (Debugging)")
            st.code(json.dumps(quiz, indent=2), language="json")

    if st.session_state.quiz_questions:
        st.subheader("\U0001F4DD Answer the Questions")
        user_answers = []

        for i, q in enumerate(st.session_state.quiz_questions):
            st.markdown(f"**Q{i + 1}: {q['question']}**")
            options = q["options"]
            user_answer = st.radio(f"Your answer for Q{i + 1}:", options, key=f"quiz_q{i}")
            user_answers.append(user_answer)

        if st.button("Submit Quiz") and not st.session_state.quiz_submitted:
            st.session_state.quiz_submitted = True
            score = 0

            st.markdown("### 📊 Results:")

            for i, q in enumerate(st.session_state.quiz_questions):
                question_text = q.get("question", f"Question {i + 1}")
                correct_answer = q.get("answer", "").strip().lower()
                user_answer = st.session_state.get(f"quiz_q{i}", "").strip().lower()

                st.markdown(f"**Q{i + 1}: {question_text}**")

                if not user_answer:
                    st.warning("❗ You did not select an answer.")
                elif user_answer == correct_answer:
                    st.success(f"✅ Your answer: {user_answer}")
                    score += 1
                else:
                    st.error(f"❌ Your answer: {user_answer}")
                    st.info(f"✅ Correct answer: {correct_answer}")

                st.markdown("---")

            st.success(f"🏁 Final Score: **{score} / {len(st.session_state.quiz_questions)}**")

            save_quiz_response(
                st.session_state.user_id,
                subject,
                st.session_state.quiz_questions,
                user_answers
            )

            save_user_progress(
                st.session_state.user_id,
                subject,
                score,
                len(st.session_state.quiz_questions)
            )

            st.session_state.score_history.append({
                "subject": subject,
                "score": score,
                "total": len(st.session_state.quiz_questions)
            })

# ----------------------------
# 📊 Tab 4: Progress Tracker
# ----------------------------
with tab4:
    st.subheader("Quiz Performance Over Time")

    progress_data = get_user_progress(st.session_state.user_id)
    if progress_data:
        df = pd.DataFrame(progress_data)
        df['accuracy'] = df['accuracy'].astype(float)

        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X('subject:N', title="Subject"),
            y=alt.Y('accuracy:Q', title="Accuracy (%)"),
            tooltip=['subject', 'score', 'total', 'accuracy']
        ).properties(
            width=600,
            height=400,
            title="Your Quiz Accuracy by Subject"
        )

        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Take some quizzes to track your progress!")
