import streamlit as st
import pandas as pd
from openai import OpenAI
from tavily import TavilyClient
import datetime

# --- ページ設定 ---
st.set_page_config(page_title="Strategic Intelligence Radar", layout="wide")

st.title("📡 Strategic Intelligence Radar")
st.caption("最新文献・技術情報の「収集」と「査定」を自動化する")

# --- APIキーの確認 ---
if "TAVILY_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("APIキーが設定されていません。SecretsにTAVILY_API_KEYとOPENAI_API_KEYを設定してください。")
    st.stop()

tavily = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- サイドバー：検索設定 ---
with st.sidebar:
    st.header("Search Parameters")
    
    # 検索キーワード
    query = st.text_input("検索キーワード:", value="Thymic regeneration cell sheet engineering")
    
    # 検索オプション
    days_back = st.slider("検索範囲（過去n日）:", 1, 365, 30)
    max_results = st.slider("取得件数:", 3, 20, 5)
    
    # 査定基準（プロンプトに埋め込む）
    focus_point = st.text_area("査定の重点ポイント:", 
                               value="胸腺上皮細胞の分化誘導効率、または細胞シートの積層技術に関する新規性があるか？")

    search_btn = st.button("レーダー照射 (検索開始)")

# --- メイン：検索と査定 ---
if search_btn:
    with st.spinner(f"Web空間をスキャン中... ({query})"):
        # 1. Tavilyで検索実行
        try:
            response = tavily.search(
                query=query, 
                search_depth="advanced", 
                max_results=max_results,
                include_domains=["nature.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov", "wiley.com", "biorxiv.org"], # 学術系に絞る例
                # exclude_domains=[] 
            )
            results = response.get("results", [])
        except Exception as e:
            st.error(f"検索エラー: {e}")
            st.stop()

    if not results:
        st.warning("関連情報が見つかりませんでした。キーワードを変えてみてください。")
    else:
        st.success(f"{len(results)} 件の情報を捕捉。AI査定を開始します...")
        
        # 結果格納用リスト
        analyzed_data = []
        progress_bar = st.progress(0)

        for i, res in enumerate(results):
            with st.spinner(f"Analyzing: {res['title'][:20]}..."):
                # 2. GPT-4oによる査定
                prompt = f"""
                あなたは再生医療分野の専門家（PI）です。以下の文献情報を読み、ユーザーの「重点ポイント」に基づいて査定してください。
                
                【重点ポイント】
                {focus_point}

                【文献情報】
                タイトル: {res['title']}
                内容スニペット: {res['content']}
                URL: {res['url']}

                【出力フォーマット】
                以下の形式で日本語で出力せよ。余計な前置きは不要。
                
                判定ランク: (S: 必読 / A: 有益 / B: 参考程度 / C: 無関係)
                要約: (50文字以内で簡潔に)
                理由: (なぜそのランクなのか、重点ポイントとどう関わるか)
                """

                ai_res = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                
                analysis_text = ai_res.choices[0].message.content
                
                # ランクの抽出（簡易的）
                rank = "B"
                if "判定ランク: S" in analysis_text: rank = "S"
                elif "判定ランク: A" in analysis_text: rank = "A"
                elif "判定ランク: C" in analysis_text: rank = "C"

                analyzed_data.append({
                    "Rank": rank,
                    "Title": res['title'],
                    "Analysis": analysis_text,
                    "URL": res['url']
                })
                
            progress_bar.progress((i + 1) / len(results))

        # --- 結果表示 ---
        st.divider()
        st.subheader("📡 Intelligence Report")

        # ランクでソート（Sが上に来るように）
        rank_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        analyzed_data.sort(key=lambda x: rank_order.get(x["Rank"], 4))

        for item in analyzed_data:
            # ランクごとの色分け
            color = "gray"
            if item["Rank"] == "S": color = "red"
            elif item["Rank"] == "A": color = "orange"
            elif item["Rank"] == "B": color = "blue"

            with st.expander(f"【{item['Rank']}】 {item['Title']}", expanded=(item["Rank"] in ["S", "A"])):
                st.markdown(f"**URL**: {item['URL']}")
                st.markdown(f"**AI査定**:\n{item['Analysis']}")
                if item["Rank"] == "S":
                    st.error("🔥 これは「重点ポイント」に深く刺さる重要文献です！")

        # CSVダウンロード
        df = pd.DataFrame(analyzed_data)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("レポートをCSVで保存", csv, f"radar_report_{datetime.date.today()}.csv", "text/csv")
