import streamlit as st
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from query_action import DatabaseSearch, ResponseGeneration, ResponseReview, NewsChatbot
import os

# 페이지 설정
st.set_page_config(
    page_title="AI Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 커스텀 CSS
st.markdown(
    """
    <style>
    /* 전체 배경색 */
    .stApp {
        background-color: white;
    }
    
    /* 사이드바 스타일링 */
    .css-1d391kg {
        padding-top: 2rem;
    }
    
    /* 아이콘 버튼 공통 스타일 */
    .icon-button {
        background: none;
        border: none;
        cursor: pointer;
        width: 24px;   /* 아이콘 크기에 맞게 조절 */
        height: 24px;
        padding: 0;
        margin: 0;
    }
    /* 아이콘 배치 컨테이너 */
    .icon-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
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
        with st.chat_message(role):
            st.markdown(content)
            if articles and role == "assistant" and len(articles) > 0:
                st.markdown("### 📚 관련 기사")
                for i in range(0, min(len(articles), 4), 2):
                    col1, col2 = st.columns(2)
                    with col1:
                        if i < len(articles):
                            art = articles[i]
                            st.markdown(
                                f"""
                                #### {i+1}. {art.get('title', '제목 없음')}
                                - 📅 발행일: {art.get('published_date', '날짜 정보 없음')}
                                - 🔗 [기사 링크]({art.get('url', '#')})
                                - 📊 카테고리: {', '.join(art.get('categories', ['미분류']))}
                                """
                            )
                    with col2:
                        if i + 1 < len(articles):
                            art = articles[i + 1]
                            st.markdown(
                                f"""
                                #### {i+2}. {art.get('title', '제목 없음')}
                                - 📅 발행일: {art.get('published_date', '날짜 정보 없음')}
                                - 🔗 [기사 링크]({art.get('url', '#')})
                                - 📊 카테고리: {', '.join(art.get('categories', ['미분류']))}
                                """
                            )

    async def process_user_input(self, user_input):
        if not user_input:
            return
        # 사용자 메시지 표시
        self.display_chat_message("user", user_input)
        with st.status("AI가 답변을 생성하고 있습니다...") as status:
            try:
                main_article, related_articles, score, response = (
                    await st.session_state.chatbot.process_query(user_input)
                )
                combined = [main_article] + related_articles if main_article else []
                self.display_chat_message("assistant", response, combined)
                if main_article:
                    st.session_state.article_history.append(main_article)
                # 히스토리에 저장
                st.session_state.search_history.append(
                    {"question": user_input, "answer": response, "articles": combined}
                )
                status.update(label="완료!", state="complete")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                status.update(label="오류 발생", state="error")


def render_sidebar():
    # 자바스크립트로 alert, console 출력하는 스크립트 삽입
    # (동작 예시를 위해 넣은 것이니, 실제 기능으로 바꾸시려면 적절히 수정하세요)
    st.markdown(
        """
        <script>
        function closeSidebar() {
            alert("Sidebar를 닫습니다(예시). Streamlit에선 기본 제공 기능이 없어 실제로는 별도 JS가 필요합니다.");
            console.log("Close sidebar clicked");
        }
        function searchChats() {
            alert("Search Chats 버튼 클릭됨 (예시)");
            console.log("Search chats clicked");
        }
        function newChat() {
            alert("새 채팅 생성 (예시)");
            console.log("New chat clicked");
        }
        </script>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        # 아이콘 영역 (HTML + JS onclick 이벤트)
        st.markdown(
            """
            <div class="icon-container">
              <!-- 첫 번째 아이콘 (close sidebar) -->
              <button class="icon-button" onclick="closeSidebar()" title="Close Sidebar">
                <!-- 아래는 streamlit 기본 toggle sidebar 아이콘을 흉내낸 SVG 예시입니다 -->
                <svg viewBox="0 0 16 16" fill="currentColor" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
                  <path fill-rule="evenodd" d="M1.5 1.5h2v13h-2v-13zm6 0h7v13h-7v-13zm5 4.5H8v1h4.5v-1z"></path>
                </svg>
              </button>
              
              <!-- 두 번째 아이콘 (search) -->
              <button class="icon-button" onclick="searchChats()" title="Search Chats">
                <svg viewBox="0 0 16 16" fill="currentColor" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
                  <path fill-rule="evenodd" d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.867-3.834zm-5.242.156a5 5 0 1 1 0-10 5 5 0 0 1 0 10z"></path>
                </svg>
              </button>
              
              <!-- 세 번째 아이콘 (new chat) -->
              <button class="icon-button" onclick="newChat()" title="New Chat">
                <svg viewBox="0 0 16 16" fill="currentColor" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
                  <path d="M15.854.146a.5.5 0 0 1 0 .708l-3.714 3.714 1.075 4.3a.25.25 0 0 1-.32.31l-4.183-1.393-3.714 3.714a.5.5 0 0 1-.708-.708l3.714-3.714-1.393-4.183a.25.25 0 0 1 .31-.32l4.3 1.075 3.714-3.714a.5.5 0 0 1 .708 0z"></path>
                </svg>
              </button>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # [대화 내용 초기화] 버튼
        if st.button("대화 내용 초기화"):
            st.session_state.messages = []
            st.session_state.search_history = []
            st.session_state.article_history = []
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

    render_sidebar()

    # 선택된 채팅 표시
    if st.session_state.get("selected_chat"):
        chat = st.session_state.selected_chat
        app.display_chat_message("user", chat["question"])
        app.display_chat_message("assistant", chat["response"], chat["articles"])

    user_input = st.chat_input("메시지를 입력하세요...")
    if user_input:
        asyncio.run(app.process_user_input(user_input))

    # 지금까지의 실시간 대화 (원하는 경우 표시)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])


if __name__ == "__main__":
    main()
