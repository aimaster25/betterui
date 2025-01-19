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
    
    /* 채팅 메시지 스타일링 */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        background-color: #f7f7f8;
    }
    
    /* 사이드바 버튼 스타일링 */
    .sidebar-button {
        background-color: transparent;
        border: none;
        padding: 0.5rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        width: 100%;
        color: #1e1e1e;
    }
    
    /* 채팅 기록 스타일링 */
    .chat-history-item {
        padding: 0.5rem;
        cursor: pointer;
        border-radius: 0.3rem;
    }
    .chat-history-item:hover {
        background-color: #f0f0f0;
    }
    
    /* 모델 선택 드롭다운 스타일링 */
    .model-selector {
        margin-top: 1rem;
        width: 100%;
    }
    
    /* 헤더 아이콘 스타일링 */
    .header-icon {
        font-size: 1.2rem;
        margin-right: 0.5rem;
        color: #666;
    }
    
    /* 검색창 스타일링 */
    .search-box {
        padding: 0.5rem;
        border-radius: 0.3rem;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)


class StreamlitChatbot:
    def __init__(self):
        # 세션 상태 초기화
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = {
                "today": [],
                "yesterday": [],
                "previous_7_days": [],
            }
        # 현재 모델
        if "current_model" not in st.session_state:
            st.session_state.current_model = "Gemini"
        # 현재 선택된 채팅
        if "selected_chat" not in st.session_state:
            st.session_state.selected_chat = None
        # 전체 대화 메시지
        if "messages" not in st.session_state:
            st.session_state.messages = []
        # 검색어
        if "search_query" not in st.session_state:
            st.session_state.search_query = ""
        # 검색 히스토리를 질문/답변/기사 형식으로 저장
        if "search_history" not in st.session_state:
            st.session_state.search_history = []
        # 기사 히스토리
        if "article_history" not in st.session_state:
            st.session_state.article_history = []
        # chatbot 초기화
        if "chatbot" not in st.session_state:
            st.session_state.chatbot = NewsChatbot()

    @staticmethod
    def init_session():
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "search_query" not in st.session_state:
            st.session_state.search_query = ""

    def display_chat_message(self, role, content, articles=None):
        """
        채팅 메시지 표시.
        articles가 있으면 "관련 기사" 섹션도 함께 표시
        """
        with st.chat_message(role):
            st.markdown(content)

            if (
                articles
                and role == "assistant"
                and isinstance(articles, list)
                and len(articles) > 0
            ):
                st.markdown("### 📚 관련 기사")

                for i in range(0, min(len(articles), 4), 2):
                    col1, col2 = st.columns(2)
                    # 첫 번째 열
                    with col1:
                        if i < len(articles) and isinstance(articles[i], dict):
                            article = articles[i]
                            st.markdown(
                                f"""
                            #### {i+1}. {article.get('title', '제목 없음')}
                            - 📅 발행일: {article.get('published_date', '날짜 정보 없음')}
                            - 🔗 [기사 링크]({article.get('url', '#')})
                            - 📊 카테고리: {', '.join(article.get('categories', ['미분류']))}
                            """
                            )
                    # 두 번째 열
                    with col2:
                        if i + 1 < len(articles) and isinstance(articles[i + 1], dict):
                            article = articles[i + 1]
                            st.markdown(
                                f"""
                            #### {i+2}. {article.get('title', '제목 없음')}
                            - 📅 발행일: {article.get('published_date', '날짜 정보 없음')}
                            - 🔗 [기사 링크]({article.get('url', '#')})
                            - 📊 카테고리: {', '.join(article.get('categories', ['미분류']))}
                            """
                            )

    async def process_user_input(self, user_input):
        """사용자 입력 처리"""
        if not user_input:
            return

        # 사용자 메시지 표시
        self.display_chat_message("user", user_input)

        # 처리 중 표시
        with st.status("AI가 답변을 생성하고 있습니다...") as status:
            try:
                # 관련 기사 검색 + 답변 생성
                status.update(label="관련 기사를 검색중입니다...")
                main_article, related_articles, score, response = (
                    await st.session_state.chatbot.process_query(user_input)
                )

                status.update(label="답변을 생성하고 있습니다...")
                # 답변 메시지 표시 (메인 기사 + 관련 기사)
                combined_articles = (
                    [main_article] + related_articles if main_article else []
                )
                self.display_chat_message("assistant", response, combined_articles)

                # 기사 히스토리 업데이트
                if main_article:
                    st.session_state.article_history.append(main_article)

                # 검색 히스토리에 질문/답변/기사 저장
                st.session_state.search_history.append(
                    {
                        "question": user_input,
                        "answer": response,
                        "articles": combined_articles,  # 주요 기사 + 관련 기사
                    }
                )

                status.update(label="완료!", state="complete")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                status.update(label="오류 발생", state="error")

    def show_analytics(self):
        """분석 정보 표시"""
        if st.session_state.article_history:
            st.header("📊 검색 분석")

            # 1. 카테고리 분포 분석
            categories = []
            for article in st.session_state.article_history:
                categories.extend(article.get("categories", ["미분류"]))

            df_categories = pd.DataFrame(categories, columns=["카테고리"])
            category_counts = df_categories["카테고리"].value_counts()

            # 2. 시간별 기사 분포 분석
            dates = [
                datetime.fromisoformat(
                    art.get("published_date", datetime.now().isoformat())
                )
                for art in st.session_state.article_history
            ]
            df_dates = pd.DataFrame(dates, columns=["발행일"])
            date_counts = df_dates["발행일"].dt.date.value_counts()

            # 분석 결과 표시
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📈 카테고리별 기사 분포")
                if not category_counts.empty:
                    st.bar_chart(category_counts)
                    st.markdown("**카테고리별 비율:**")
                    for cat, count in category_counts.items():
                        percentage = (count / len(categories)) * 100
                        st.write(f"- {cat}: {percentage:.1f}% ({count}건)")
                else:
                    st.info("아직 카테고리 데이터가 없습니다.")

            with col2:
                st.subheader("📅 일자별 기사 분포")
                if not date_counts.empty:
                    st.line_chart(date_counts)
                    st.markdown("**날짜별 기사 수:**")
                    for date, count in date_counts.sort_index(ascending=False).items():
                        st.write(f"- {date.strftime('%Y-%m-%d')}: {count}건")
                else:
                    st.info("아직 날짜 데이터가 없습니다.")

            # 3. 검색 통계
            st.subheader("🔍 검색 통계")
            col3, col4, col5 = st.columns(3)
            with col3:
                st.metric(
                    label="총 검색 수", value=len(st.session_state.search_history)
                )
            with col4:
                st.metric(
                    label="검색된 총 기사 수",
                    value=len(st.session_state.article_history),
                )
            with col5:
                if st.session_state.article_history:
                    latest_article = max(
                        st.session_state.article_history,
                        key=lambda x: x.get("published_date", ""),
                    )
                    st.metric(
                        label="최신 기사 날짜",
                        value=datetime.fromisoformat(
                            latest_article.get(
                                "published_date", datetime.now().isoformat()
                            )
                        ).strftime("%Y-%m-%d"),
                    )

            # 4. 최근 검색어 히스토리
            if st.session_state.search_history:
                st.subheader("🕒 최근 검색어")
                recent_searches = st.session_state.search_history[-5:]
                for item in reversed(recent_searches):
                    st.text(f"• {item['question']}")
        else:
            st.info("아직 검색 결과가 없습니다. 질문을 입력해주세요!")


def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        # 아이콘 영역
        st.markdown(
            """
            <div style='display: flex; gap: 1rem; margin-bottom: 1rem;'>
                <span title="Close Sidebar" style="font-size:1.3rem; cursor:pointer;">🗙</span>
                <span title="Search Chats" style="font-size:1.3rem; cursor:pointer;">🔎</span>
                <span title="New Chat" style="font-size:1.3rem; cursor:pointer;">📝</span>
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

        # 검색 히스토리 목록
        st.markdown("### 검색 히스토리")
        for i, item in enumerate(st.session_state.search_history):
            q = item["question"]
            if st.button(q if q else "무제", key=f"search_history_{i}"):
                # 클릭 시 선택된 채팅으로 저장 -> 답변 및 기사 목록까지 함께 보여주기
                st.session_state.selected_chat = {
                    "question": item["question"],
                    "response": item["answer"],
                    "articles": item["articles"],  # ← 관련 기사 목록까지 복원
                }


def main():
    app = StreamlitChatbot()
    app.init_session()

    st.markdown("## AI 뉴스에 대해 무엇이든 물어보세요")
    st.selectbox("AI 모델 선택", ["Gemini", "GPT-4", "BERT"], key="current_model")
    st.write("어떤 뉴스를 알고 싶으세요?")

    # 사이드바 출력
    render_sidebar()

    # 만약 selected_chat이 있으면, 해당 검색(질문+답변+기사) 복원
    if st.session_state.selected_chat:
        # 유저가 했던 질문 복원
        app.display_chat_message("user", st.session_state.selected_chat["question"])
        # 당시 챗봇 답변 + 기사 목록 복원
        app.display_chat_message(
            "assistant",
            st.session_state.selected_chat["response"],
            st.session_state.selected_chat["articles"],
        )
    else:
        st.markdown("")

    # 사용자 새 입력 처리
    user_input = st.chat_input("메시지를 입력하세요...")
    if user_input:
        asyncio.run(app.process_user_input(user_input))

    # (옵션) 지금까지의 대화 메시지 표시
    # 만약 "검색 히스토리"가 아닌, 매 실시간 입력에 대해서도 누적 기록을 보고 싶다면:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


if __name__ == "__main__":
    main()
