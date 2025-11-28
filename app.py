import streamlit as st
import json
import re
import google.generativeai as genai

# --- 設定 ---
st.set_page_config(page_title="Verbo Master", page_icon="🇪🇸")

# APIキーの読み込み
# Streamlit CloudのSecretsから読み込む設定
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    # Secretsが設定されていない場合のエラー表示
    st.error("APIキーが設定されていません。Streamlit CloudのSettings > Secretsに GEMINI_API_KEY を設定してください。")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 辞書データの読み込み ---
@st.cache_data
def load_dictionary():
    try:
        with open('spanish_dict.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

dictionary_list = load_dictionary()

# --- 検索ロジック ---
def search_dictionary(text):
    if not dictionary_list:
        return "（辞書データを読み込めませんでした）"
    
    words = re.split(r'[^a-záéíóúñü]+', text.lower())
    results = []
    found_set = set()

    for w in words:
        if len(w) < 2 or w in found_set:
            continue
        
        # 辞書から検索
        for entry in dictionary_list:
            if entry['word'].lower() == w:
                meaning = entry['meaning'].replace("∥", "\n").replace("―", "-")
                results.append(f"・**{entry['word']}** : {meaning}")
                found_set.add(w)
                break 
    
    if not results:
        return "（辞書に一致する単語はありませんでした）"
    
    return "\n\n".join(results)

# --- AI解説ロジック ---
def analyze_text_with_gemini(user_text, dictionary_info):
    prompt = f"""
    あなたはスペイン語教育のプロフェッショナルです。
    以下の「参照辞書データ」を最優先で使用し、ユーザーのテキストを解説・翻訳してください。

    ### ユーザーの入力テキスト:
    {user_text}

    ### 参照すべき辞書データ:
    {dictionary_info}

    ### 指示
    1. 単語解説:
       - 文頭から順に単語を解説してください。
       - 辞書データにある意味を必ず使用してください。
       - 定冠詞は除外してください。
    
    2. 日本語訳:
       - 自然な日本語訳を作成してください。

    ### 出力フォーマット
    解説と翻訳の間には区切り文字「|||」を入れてください。
    箇条書きは「・」を使用してください。
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # 整形
        text = text.replace("**", "").replace("* ", "・").replace("- ", "・")
        
        parts = text.split("|||")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
        else:
            return text, "（翻訳の分割に失敗しました）"
            
    except Exception as e:
        return f"エラー: {e}", ""

# --- 画面構築 (UI) ---
st.title("Verbo Master")
st.write("内蔵の辞書データとAIを組み合わせた学習ツールです。")

input_text = st.text_area("スペイン語を入力してください", height=100)

if st.button("解説スタート", type="primary"):
    if not input_text:
        st.warning("文章を入力してください")
    else:
        with st.spinner('AIが考え中...'):
            # 1. 辞書検索
            dict_result = search_dictionary(input_text)
            
            # 2. AI解説
            explanation, translation = analyze_text_with_gemini(input_text, dict_result)

            # --- 結果表示 ---
            st.success("完了しました！")
            
            tab1, tab2 = st.tabs(["単語解説", "日本語訳"])
            
            with tab1:
                if "（辞書に一致" not in dict_result:
                    st.info("【辞書データ】")
                    st.markdown(dict_result)
                    st.divider()
                st.markdown("### AI解説")
                st.write(explanation)
                
            with tab2:
                st.markdown("### 日本語訳")
                st.markdown(f"#### {translation}")


