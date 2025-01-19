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
        if "current_model" not in st.session_state:
            st.session_state.current_model = "Gemini"
        if "selected_chat" not in st.session_state:
            st.session_state.selected_chat = None
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "search_query" not in st.session_state:
            st.session_state.search_query = ""
        if "search_history" not in st.session_state:  # 추가
            st.session_state.search_history = set()  # 추가
        if "article_history" not in st.session_state:  # 추가
            st.session_state.article_history = []  # 추가
        # chatbot 초기화 추가
        if "chatbot" not in st.session_state:
            st.session_state.chatbot = NewsChatbot()

    @staticmethod
    def init_session():
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "search_query" not in st.session_state:
            st.session_state.search_query = ""

    @staticmethod
    def categorize_chats():
        """채팅을 날짜별로 분류"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        # 실제 애플리케이션에서는 데이터베이스에서 가져올 수 있음
        sample_chats = [
            {
                "id": 1,
                "date": today,
                "question": "",
            },
            {
                "id": 2,
                "date": yesterday,
                "question": "",
            },
            {
                "id": 3,
                "date": week_ago,
                "question": "",
            },
        ]

        return sample_chats

    def display_article_info(self, article, score=None):
        """기사 정보 표시"""
        with st.container():
            st.markdown(
                f"""
                <div class="article-card">
                    <h4>📰 {article['title']}</h4>
                    <p><b>발행일:</b> {article.get('published_date', '날짜 정보 없음')}</p>
                    {f'<p><b>관련도:</b> {score:.2f}%</p>' if score else ''}
                    <p><b>🔗 기사 링크:</b> <a href="{article['url']}" target="_blank">{article['url']}</a></p>
                    <p><b>카테고리:</b> {', '.join(article.get('categories', ['미분류']))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    def display_chat_message(self, role, content, articles=None):
        """채팅 메시지 표시"""
        with st.chat_message(role):
            st.markdown(content)

            if articles and role == "assistant" and isinstance(articles, list):
                st.markdown("### 📚 관련 기사")

                # 기본 정보 표시
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
        st.session_state.search_history.add(user_input)

        # 처리 중 표시
        with st.status("AI가 답변을 생성하고 있습니다...") as status:
            try:
                # 챗봇 응답 생성
                status.update(label="관련 기사를 검색중입니다...")
                main_article, related_articles, score, response = (
                    await st.session_state.chatbot.process_query(user_input)
                )

                status.update(label="답변을 생성하고 있습니다...")
                # 응답 저장 및 표시 - 기존 display_chat_message 메서드 사용
                self.display_chat_message(
                    "assistant",
                    response,
                    [main_article] + related_articles if main_article else None,
                )

                # 기사 히스토리 업데이트
                if main_article:
                    st.session_state.article_history.append(main_article)

                status.update(label="완료!", state="complete")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                status.update(label="오류 발생", state="error")

                # 기사 히스토리 업데이트
                if main_article:
                    st.session_state.article_history.append(main_article)

                status.update(label="완료!", state="complete")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
                status.update(label="오류 발생", state="error")

    def show_analytics(self):
        """분석 정보 표시"""
        if st.session_state.article_history:  # 기사 히스토리가 있는 경우만 표시
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
                    # 카테고리별 비율 표시
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
                    # 최신순으로 날짜별 기사 수 표시
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
                recent_searches = list(st.session_state.search_history)[-5:]  # 최근 5개
                for query in reversed(recent_searches):
                    st.text(f"• {query}")
        else:
            st.info("아직 검색 결과가 없습니다. 질문을 입력해주세요!")


def render_sidebar(chats):  # chats 파라미터 추가
    """사이드바 렌더링"""
    with st.sidebar:
        # 모델 선택 드롭다운
        st.selectbox("AI 모델 선택", ["Gemini"], key="current_model", index=0)

        # 검색 및 새 채팅 버튼
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.button("🔍", key="search_button", help="대화 검색")
        with col2:
            st.button("✏️", key="new_chat_button", help="새 채팅")

        # 검색창 (검색 버튼 클릭 시 표시)
        if st.session_state.get("search_button", False):
            st.text_input(
                "검색어 입력", key="search_query", placeholder="검색어를 입력하세요..."
            )

        # 채팅 기록
        st.markdown("### Today")
        for chat in [c for c in chats if c["date"] == datetime.now().date()]:
            if st.button(
                chat["question"],
                key=f"chat_{chat['id']}",
                help=chat["date"].strftime("%Y-%m-%d"),
            ):
                st.session_state.selected_chat = chat

        st.markdown("### Yesterday")
        for chat in [
            c
            for c in chats  # categorize_chats()를 chats로 변경
            if c["date"] == (datetime.now().date() - timedelta(days=1))
        ]:
            if st.button(
                chat["question"],
                key=f"chat_{chat['id']}",
                help=chat["date"].strftime("%Y-%m-%d"),
            ):
                st.session_state.selected_chat = chat

        st.markdown("### Previous 7 Days")
        for chat in [
            c
            for c in chats  # categorize_chats()를 chats로 변경
            if c["date"] < (datetime.now().date() - timedelta(days=1))
        ]:
            if st.button(
                chat["question"],
                key=f"chat_{chat['id']}",
                help=chat["date"].strftime("%Y-%m-%d"),
            ):
                st.session_state.selected_chat = chat


def main():
    app = StreamlitChatbot()
    app.init_session()

    # categorize_chats의 결과를 render_sidebar에 전달
    chats = app.categorize_chats()
    render_sidebar(chats)

    # 메인 채팅 영역
    if st.session_state.selected_chat:
        st.markdown(f"**Question:** {st.session_state.selected_chat['question']}")
        st.markdown(f"**Response:** {st.session_state.selected_chat['response']}")
    else:
        st.markdown("새로운 대화를 시작하세요!")

    # 채팅 입력
    user_input = st.chat_input("메시지를 입력하세요...")
    if user_input:
        asyncio.run(app.process_user_input(user_input))

    # 대화 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


if __name__ == "__main__":
    main()
