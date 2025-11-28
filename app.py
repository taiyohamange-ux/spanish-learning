import streamlit as st
import json
import re
import google.generativeai as genai

# --- ページ設定 ---
st.set_page_config(page_title="Verbo Master", page_icon="🇪🇸")

# --- APIキーの読み込み ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("APIキーが設定されていません。")
    st.stop()

# Geminiの設定 (正しいモデル名に戻しました)
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 辞書データの読み込み ---
@st.cache_data
def load_dictionary():
    try:
        with open('spanish_dict.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

dictionary_list = load_dictionary()

# --- 辞書検索ロジック ---
def search_dictionary(text):
    if not dictionary_list:
        return "（辞書データを読み込めませんでした）"
    
    words = re.split(r'[^a-záéíóúñü]+', text.lower())
    results = []
    found_set = set()

    for w in words:
        if len(w) < 2 or w in found_set:
            continue
        
        for entry in dictionary_list:
            if entry['word'].lower() == w:
                # 辞書の見栄えを調整
                meaning = entry['meaning'].replace("∥", "\n").replace("―", "-")
                results.append(f"・**{entry['word']}** : {meaning}")
                found_set.add(w)
                break 
    
    if not results:
        return "（辞書に一致する単語はありませんでした）"
    
    return "\n\n".join(results)

# --- AI解説・翻訳ロジック ---
def analyze_text_with_gemini(user_text, dictionary_info):
    prompt = f"""
    あなたはスペイン語教育のプロフェッショナルです。
    以下の「参照辞書データ」とユーザーのテキストを基に、解説と翻訳を行ってください。

    ### ユーザーの入力テキスト:
    {user_text}

    ### 参照すべき辞書データ:
    {dictionary_info}

    ### 指示
    1. 単語解説:
       - 文頭から順に重要な単語を解説してください。
       - **各単語は必ず「改行」して、縦にリスト表示してください。**
       - 辞書データは参考にしますが、文脈に合わない場合（特に前置詞 de, a, y などが「文字」として定義されている場合）は、辞書の定義を無視して、文脈に即した正しい文法説明をしてください。
       - 定冠詞 (el, la, los, las) は解説リストに含めないでください。
    
    2. 日本語訳:
       - 辞書の定義を直訳せず、文脈を理解した自然な日本語に翻訳してください。

    ### 重要：出力フォーマット
    解説と翻訳の間には、区切り文字として「|||」を挿入してください。
    箇条書きの頭には「・」を使用してください。
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # --- 強制整形処理 ---
        # 1. 太字記号を削除
        text = text.replace("**", "")
        
        # 2. 箇条書き記号を「・」に統一
        text = text.replace("* ", "・").replace("- ", "・")
        
        # 3. 【最強の改行処理】「・」を「改行2つ + ・」に強制置換
        # これで、どんな状態でも必ず改行されます
        text = text.replace("・", "\n\n・")
        
        # 4. 改行が増えすぎた場合の整理（改行3つ以上を2つに戻す）
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        
        # 区切り文字で分割
        parts = text.split("|||")
        
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
        else:
            return text, "（翻訳データの分割に失敗しましたが、解説に含まれている可能性があります）"
            
    except Exception as e:
        return f"通信エラー: {e}", ""

# --- アプリの画面構成 (UI) ---
st.title("Verbo Master")
st.write("辞書データとAIを組み合わせた、あなただけの学習ツールです。")

input_text = st.text_area("スペイン語を入力してください", height=150, placeholder="例: El abogado come una manzana.")

if st.button("解説スタート", type="primary"):
    if not input_text:
        st.warning("文章を入力してください")
    else:
        with st.spinner('辞書を引いて、AIが解説中...'):
            # 1. 辞書検索
            dict_result = search_dictionary(input_text)
            
            # 2. AI解説 & 翻訳
            explanation, translation = analyze_text_with_gemini(input_text, dict_result)

            st.success("完了しました！")
            
            tab1, tab2 = st.tabs(["単語解説", "🇯🇵 日本語訳"])
            
            with tab1:
                if "（辞書に一致" not in dict_result:
                    with st.expander("📚 辞書の検索結果を見る", expanded=True):
                        st.markdown(dict_result)
                    st.divider()
                
                st.markdown("### 📝 AIによる文法解説")
                # AIの解説を表示
                st.markdown(explanation)
                
            with tab2:
                st.markdown("### 🇯🇵 日本語訳")
                st.info(translation)

