import streamlit as st
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import os

# 여기는 사용자의 NewsChatbot 모듈(예시)
from query_action import NewsChatbot

# 페이지 설정
st.set_page_config(
    page_title="AI Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 간단 CSS
st.markdown(
    """
    <style>
    /* 사이드바 여백, 버튼 스타일 정도만 살짝 조정 */
    .css-1d391kg {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


class StreamlitChatbot:
    def __init__(self):
        if "search_history" not in st.session_state:
            st.session_state.search_history = []
        if "selected_chat" not in st.session_state:
            st.session_state.selected_chat = None
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "article_history" not in st.session_state:
            st.session_state.article_history = []
        if "chatbot" not in st.session_state:
            st.session_state.chatbot = NewsChatbot()

    def display_chat_message(self, role, content, articles=None):
        """채팅 메시지 표시"""
        with st.chat_message(role):
            st.markdown(content)
            if articles and role == "assistant" and len(articles) > 0:
                st.markdown("### 📚 관련 기사")
                for i in range(0, min(len(articles), 4), 2):
                    col1, col2 = st.columns(2)
                    if i < len(articles):
                        art = articles[i]
                        with col1:
                            st.markdown(
                                f"""
                                #### {i+1}. {art.get('title', '제목 없음')}
                                - 📅 발행일: {art.get('published_date', '날짜 정보 없음')}
                                - 🔗 [기사 링크]({art.get('url', '#')})
                                - 📊 카테고리: {', '.join(art.get('categories', ['미분류']))}
                                """
                            )
                    if i + 1 < len(articles):
                        art = articles[i + 1]
                        with col2:
                            st.markdown(
                                f"""
                                #### {i+2}. {art.get('title', '제목 없음')}
                                - 📅 발행일: {art.get('published_date', '날짜 정보 없음')}
                                - 🔗 [기사 링크]({art.get('url', '#')})
                                - 📊 카테고리: {', '.join(art.get('categories', ['미분류']))}
                                """
                            )

    async def process_user_input(self, user_input):
        """사용자 입력을 처리 -> NewsChatbot으로부터 답변, 관련 기사 받아 표시"""
        if not user_input:
            return
        # 사용자 메시지 먼저 표시
        self.display_chat_message("user", user_input)

        with st.status("AI가 답변을 생성하고 있습니다...") as status:
            try:
                main_article, related_articles, score, response = (
                    await st.session_state.chatbot.process_query(user_input)
                )
                combined = [main_article] + related_articles if main_article else []
                self.display_chat_message("assistant", response, combined)

                # 기사 히스토리 업데이트
                if main_article:
                    st.session_state.article_history.append(main_article)

                # 검색 히스토리 저장
                st.session_state.search_history.append(
                    {"question": user_input, "answer": response, "articles": combined}
                )

                status.update(label="완료!", state="complete")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                status.update(label="오류 발생", state="error")


def render_sidebar():
    """사이드바에 아이콘 버튼 + 대화 초기화 + 검색 히스토리 표시"""
    with st.sidebar:
        st.markdown("#### 메뉴")

        # 아이콘 버튼들: Close, Search, New Chat
        col1, col2, col3 = st.columns(3)
        with col1:
            close_pressed = st.button(
                "",  # 라벨은 공백
                help="Close Sidebar (예시)",  # 마우스 올리면 뜨는 툴팁
                key="close_btn",
                icon="arrow-bar-left",  # Streamlit이 지원하는 Bootstrap 아이콘
            )
        with col2:
            search_pressed = st.button(
                "", help="Search Chats (예시)", key="search_btn", icon="search"
            )
        with col3:
            newchat_pressed = st.button(
                "", help="New Chat (예시)", key="newchat_btn", icon="pencil"
            )

        # 각 버튼이 눌렸을 때 동작
        if close_pressed:
            st.toast(
                "Close 버튼이 눌렸습니다(예시). (사이드바 실제 닫기는 별도 기능 필요)"
            )
        if search_pressed:
            st.toast("Search 버튼이 눌렸습니다(예시).")
        if newchat_pressed:
            st.toast("New Chat 버튼이 눌렸습니다(예시).")

        # 대화 내용 초기화
        if st.button("대화 내용 초기화"):
            st.session_state.messages.clear()
            st.session_state.search_history.clear()
            st.session_state.article_history.clear()
            st.session_state.selected_chat = None
            st.experimental_rerun()

        # 검색 히스토리
        st.markdown("### 검색 히스토리")
        for i, item in enumerate(st.session_state.search_history):
            q = item["question"]
            if st.button(q if q else "무제", key=f"search_history_{i}"):
                st.session_state.selected_chat = {
                    "question": item["question"],
                    "response": item["answer"],
                    "articles": item["articles"],
                }


def main():
    app = StreamlitChatbot()

    st.markdown("## AI 뉴스에 대해 무엇이든 물어보세요")
    st.selectbox("AI 모델 선택", ["Gemini", "GPT-4", "BERT"], key="current_model")
    st.write("어떤 뉴스를 알고 싶으세요?")

    # 사이드바 호출
    render_sidebar()

    # 만약 검색 히스토리 등을 통해 selected_chat이 설정되었다면 표시
    if st.session_state.get("selected_chat"):
        chat = st.session_state.selected_chat
        app.display_chat_message("user", chat["question"])
        app.display_chat_message("assistant", chat["response"], chat["articles"])

    # 채팅 입력
    user_input = st.chat_input("메시지를 입력하세요...")
    if user_input:
        asyncio.run(app.process_user_input(user_input))

    # 지금까지의 대화 메시지
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])


if __name__ == "__main__":
    main()
