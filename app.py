import streamlit as st
import pandas as pd
from openai import OpenAI
from tavily import TavilyClient
import datetime

# --- ページ設定 ---
st.set_page_config(page_title="Strategic Radar: 3-Perspectives", layout="wide")

st.title("📡 Strategic Intelligence Radar")
st.caption("視点を切り替え、広範な学習から厳格な業務判断まで対応する")

# --- API設定 ---
if "TAVILY_API_KEY" not in st.secrets or "OPENAI_API_KEY" not in st.secrets:
    st.error("APIキー設定が必要です。")
    st.stop()

tavily = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- サイドバー：設定 ---
with st.sidebar:
    st.header("🔍 Search Settings")
    
    query = st.text_input("検索キーワード:", value="Thymic regeneration cell sheet")
    
    st.divider()
    st.subheader("視点（Persona）の選択")
    
    # 3つのモード選択
    persona_mode = st.radio("AIの視点:", ["学生", "研究生", "エンジニア"])
    
    st.info(f"現在のモード: **{persona_mode}**")
    if persona_mode == "学生":
        st.caption("特徴: コスト無視。検索ワードに少しかすっていればOK。幅広く情報を収集するフェーズ。")
    elif persona_mode == "研究生":
        st.caption("特徴: コスト無視。ただし検索ワードとの適合度、加点・減点基準は厳格に守る。学術的探求フェーズ。")
    elif persona_mode == "エンジニア":
        st.caption("特徴: コスト意識・実用性重視。検索ワード適合度、加点・減点基準を厳格に適用。実装・製造フェーズ。")

    st.divider()
    
    # 加点・減点はモードによって重要度が変わるが、入力欄は用意しておく
    focus_point = st.text_area("加点要素 (Focus):", 
                               value="胸腺上皮細胞の分化効率、3次元構造の構築手法")
    exclude_criteria = st.text_area("減点要素 (Exclude):",
                                    value="総説(Review)、マウス実験のみで臨床的示唆がないもの")

    days_back = st.slider("検索範囲（過去n日）:", 1, 365, 30)
    max_results = st.slider("取得件数:", 3, 20, 5)
    
    search_btn = st.button("レーダー照射")

# --- メイン処理 ---
if search_btn:
    with st.spinner(f"Web空間をスキャン中... ({query})"):
        try:
            # 検索自体は共通で行う
            response = tavily.search(
                query=query, 
                search_depth="advanced", 
                max_results=max_results,
                include_domains=["nature.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov", "biorxiv.org"]
            )
            results = response.get("results", [])
        except Exception as e:
            st.error(f"検索エラー: {e}")
            st.stop()

    if not results:
        st.warning("ヒットなし。キーワードを調整してください。")
    else:
        st.success(f"{len(results)} 件捕捉。**{persona_mode}** の視点で査定を開始します。")
        
        analyzed_data = []
        progress_bar = st.progress(0)

        for i, res in enumerate(results):
            
            # --- プロンプトの動的生成（ここが肝） ---
            system_instruction = ""
            
            if persona_mode == "学生":
                system_instruction = f"""
                あなたは「好奇心旺盛な学生」です。
                【行動指針】
                1. **コストや実現性は気にするな**。面白そうなら評価せよ。
                2. 検索キーワードに**少しかすっている程度でも「関連あり」**とみなして広く拾え。
                3. 難しい専門用語よりも、概念的な理解を重視せよ。
                4. ユーザーの「減点要素」は参考程度にし、厳しく弾きすぎるな。
                """
            
            elif persona_mode == "研究生":
                system_instruction = f"""
                あなたは「真理を探究する研究生」です。
                【行動指針】
                1. **コストは度外視**せよ。重要なのは「新規性」と「メカニズム」だ。
                2. 検索キーワードとの**適合度は厳格に判定**せよ。関係ないものは容赦なく切り捨てろ（Cランク）。
                3. ユーザーの**「加点要素」「減点要素」を最優先**で考慮せよ。
                4. 論文としての質の高さ（エビデンスレベル）を重視せよ。
                """
            
            elif persona_mode == "エンジニア":
                system_instruction = f"""
                あなたは「実用化を目指すMSATエンジニア」です。
                【行動指針】
                1. **コスト、製造実現性、スケールアップの可否**を常に意識せよ。高コストすぎる手法は減点対象だ。
                2. 検索キーワードとの**適合度は厳格に判定**せよ。
                3. ユーザーの**「加点要素」「減点要素」を最優先**で考慮せよ。
                4. 「現場で使えるか？」という視点で辛口に評価せよ。
                """

            prompt = f"""
            {system_instruction}

            以下の文献情報を査定し、ランク付けとコメントを行ってください。

            【ユーザーの加点基準】
            {focus_point}

            【ユーザーの減点基準】
            {exclude_criteria}

            【対象文献】
            タイトル: {res['title']}
            内容: {res['content']}
            URL: {res['url']}

            【出力フォーマット】
            判定ランク: (S/A/B/C)
            要約: (簡潔に)
            コメント: (指定された視点での評価コメント)
            """

            try:
                ai_res = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4
                )
                text = ai_res.choices[0].message.content
                
                # ランク抽出
                rank = "B"
                if "判定ランク: S" in text: rank = "S"
                elif "判定ランク: A" in text: rank = "A"
                elif "判定ランク: C" in text: rank = "C"

                analyzed_data.append({"Rank": rank, "Title": res['title'], "Analysis": text, "URL": res['url']})
            except:
                pass
            
            progress_bar.progress((i + 1) / len(results))

        # --- 結果表示 ---
        st.divider()
        st.subheader(f"📡 Report ({persona_mode} View)")

        # 学生モードならCランク（無関係）以外は全部表示するなど、表示ロジックも少し変える
        # ここでは基本ソートのみ実装
        rank_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        analyzed_data.sort(key=lambda x: rank_order.get(x["Rank"], 4))

        for item in analyzed_data:
            # アイコン変化
            icon = "📄"
            if item["Rank"] == "S": icon = "🔥"
            elif item["Rank"] == "C": icon = "🗑️"
            
            # 学生モードならBランクでも大きく表示、エンジニアなら厳しく隠すなどの調整
            is_expanded = False
            if persona_mode == "学生":
                is_expanded = item["Rank"] in ["S", "A", "B"] # 広く見る
            else:
                is_expanded = item["Rank"] in ["S", "A"] # 厳しく見る

            with st.expander(f"{icon} 【{item['Rank']}】 {item['Title']}", expanded=is_expanded):
                st.markdown(f"**URL**: {item['URL']}")
                st.info(item["Analysis"])

        # CSV保存
        df = pd.DataFrame(analyzed_data)
        st.download_button("レポート保存 (CSV)", df.to_csv(index=False).encode('utf-8'), "radar_report.csv", "text/csv")
