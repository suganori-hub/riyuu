import streamlit as st
import re
import google.generativeai as genai

# ページ設定
st.set_page_config(
    page_title="大学・専門学校 志望理由書文章化支援アプリ",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# タイトル
st.title("📝 大学・専門学校 志望理由書文章化支援アプリ")
st.markdown("---")

# NGワードとアドバイスの定義
NG_WORDS = {
    "魅力を感じた": "「どの特色に、なぜ惹かれたのか」を自分の言葉で具体的に書きましょう。",
    "教育方針に共感した": "「どの教育方針に、自分のどのような経験や姿勢が合致しているか」を具体的に書きましょう。",
    "さまざまなこと": "「さまざまな」という言葉を避け、具体的に「何を学ぶか」を書きましょう。",
    "多くのこと": "具体的に「何について学ぶか」を書きましょう。",
    "人の役に立ちたい": "「誰の、どのような課題に、どう関わりたいか」と言い換えましょう。",
    "社会に貢献したい": "「どのような課題に関わる形で、どう社会に貢献したいか」を具体的に書きましょう。",
    "将来に生かしたい": "具体的に「どのような場面で、どう生かすか」を書きましょう。",
    "視野を広げる": "視野を広げた結果、「何を成し遂げたいか」を書きましょう。",
    "深く学びたい": "「深く」ではなく、具体的に「どのような方法（調査・実験など）で学ぶか」を書きましょう。"
}

# 共通の解析・アドバイス関数
def analyze_text(text):
    warnings = []
    # 1. NGワードチェック
    for word, advice in NG_WORDS.items():
        if word in text:
            warnings.append(f"⚠️ **「{word}」が含まれています**: {advice}")
    
    # 2. 一文の長さチェック (句点「。」で分割)
    sentences = re.split(r'[。！？]', text)
    for s in sentences:
        s = s.strip()
        if len(s) > 60:
            warnings.append(f"⚠️ **一文が長すぎます ({len(s)}文字)**: 「{s[:15]}...」の文は60文字を超えています。二文に分けられないか確認しましょう。")
            
    return warnings

# サイドバー
st.sidebar.header("💡 アプリの使い方")
st.sidebar.write("""
このアプリは、大学や専門学校の推薦・総合型選抜に対応した志望理由書作成ワークシートをシステム化したものです。
コピペを使って段階的（4ステップ）に進めることで、学校（大学・専門学校）に「ここで学ぶ必然性」が伝わる強力な文章を練り上げ、最後には模擬面接で本番対策を行います。
""")

# AI設定 (サイドバー)
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 AI設定 (壁打ち・添削用)")
st.sidebar.write("「AI壁打ち」や「AI厳格添削」、「模擬面接」機能を利用するには、GeminiのAPIキーが必要です。")
api_key_input = st.sidebar.text_input("Gemini API Key", type="password", help="Google AI Studio等で取得したAPIキーを入力してください。")
if api_key_input:
    st.session_state.gemini_api_key = api_key_input

st.sidebar.caption("💡 先生へ: Streamlit Cloudの Secrets に `GEMINI_API_KEY` を登録しておくと、生徒がキーを入力しなくても最初からすべてのAI機能を使えるようになります。")

# AIモデルの選択
st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AIモデルの設定")
model_options = [
    "gemini-3.6-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-3.6-pro",
    "gemini-1.5-pro",
]
selected_model = st.sidebar.selectbox(
    "使用するAIモデルを選択してください:",
    options=model_options,
    index=0,
    help="お使いのAPIキーのプランや時期によって、利用可能なモデルが異なります。エラーが出る場合は、別のモデル（gemini-2.0-flash など）に切り替えてみてください。"
)

custom_model_enabled = st.sidebar.checkbox("別のモデル名を直接入力する")
if custom_model_enabled:
    selected_model = st.sidebar.text_input("モデル名を入力（例: gemini-3.6-flash）", value="gemini-3.6-flash")

api_key = st.session_state.get("gemini_api_key") or st.secrets.get("GEMINI_API_KEY")

# セッション状態の初期化
if "theme" not in st.session_state: st.session_state.theme = ""
if "method" not in st.session_state: st.session_state.method = ""
if "position" not in st.session_state: st.session_state.position = ""
if "target" not in st.session_state: st.session_state.target = ""

if "step1_sentence" not in st.session_state:
    st.session_state.step1_sentence = ""

for i in range(1, 6):
    if f"step2_p{i}" not in st.session_state: st.session_state[f"step2_p{i}"] = ""

if "step2_compiled" not in st.session_state: st.session_state.step2_compiled = ""
if "step3_input" not in st.session_state: st.session_state.step3_input = ""

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "こんにちは！大学・専門学校の推薦合格を目指して、志望理由書の「核（中心文）」を一緒に固めていきましょう！\n\nまずは、あなたが今高校での探究活動や日常生活の中で、もっとも「疑問に思っていること」や「解決したい地域・社会の課題」について、短くても良いので教えてください！"}
    ]

if "step2_messages" not in st.session_state:
    st.session_state.step2_messages = [
        {"role": "assistant", "content": "ステップ①で決めた「中心文」をもとに、5つの段落（きっかけ、研究内容、学校の理由、将来像、社会貢献）を1つずつ一緒に作っていきましょう！\n\nまずは、上部の「ガイドライン貼り付け欄」にステップ①で決めた中心文をペーストしてください。貼り付けたら、どの段落から相談したいか教えてくださいね！"}
    ]

if "step4_messages" not in st.session_state:
    st.session_state.step4_messages = []

if "step4_active" not in st.session_state:
    st.session_state.step4_active = False

if "step4_feedback" not in st.session_state:
    st.session_state.step4_feedback = ""

# AIステップ1用のシステムプロンプト (壁打ち特化)
system_instruction_step1 = """あなたは大学や専門学校の推薦型選抜・総合型選抜を志望する高校生の指導を行う、極めて優秀で熱意ある進路指導アドバイザーです。
生徒の「志望理由の核（中心文）」を妥協なく、かつ温かく一緒に作るため、対話を通じて以下の4つの要素を引き出してください。

1. 【テーマ】（例: 地域コミュニティの衰退問題、再生可能エネルギーの普及、不登校問題、自動車のデザインなど、具体的に探究・研究・勉強したい内容）
2. 【視点・方法】（例: 自治体と市民の協働という視点、心理学的な実験、データ分析、アンケート調査、実技実習など、どうやってそれを深く学ぶか）
3. 【立場】（例: 地域コーディネーター、開発エンジニア、臨床心理士、グラフィックデザイナーなど、将来どんな役割・職業で活躍したいか）
4. 【対象・課題】（例: 高齢化が進む限界集落、心の病を抱える子どもたち、魅力が伝わっていない中小企業の製品など、誰のどんな課題に貢献したいか）

対話のルール：
- 一度にすべての要素を聞かないでください。生徒が答えやすいよう、まずは「今、一番関心があること」や「将来やりたいこと」などを聞き、1問ずつ丁寧に対話を進めてください。
- 生徒の回答が曖昧（例：「経済を学びたい」「人の役に立ちたい」など）な場合、絶対にそのまま認めず、「具体的にどんな現象に興味がありますか？」「どんな人のどんな課題に？」と、優しく掘り下げてください。
- 特に「アドミッション・ポリシー（AP）に共感した」や「貴校に魅力を感じた」という丸写しの言葉は却下し、「どの特色に、なぜ惹かれたのか」を言葉にさせてください。
- 4つの要素が引き出せたら、以下のテンプレートに当てはめた「中心文」を提案してください：
  「私は【テーマ】について、【視点・方法】から研究し、将来【立場】として、【対象・課題】に貢献したい。」
- 生徒がその提案に納得したら、必ず、会話の最後に以下の形式で4つの要素を出力してください。結果以外の余計な文章はタグの後ろに絶対に付けないでください。

[RESULT]
THEME: {抽出したテーマ}
METHOD: {抽出した視点・方法}
POSITION: {抽出した立場}
TARGET: {抽出した対象・課題}
[/RESULT]
"""

# AIステップ2用のシステムプロンプト (段落肉付け壁打ち)
system_instruction_step2 = """あなたは大学や専門学校の推薦型選抜・総合型選抜を志望する高校生の指導を行う、極めて優秀で熱意ある進路指導アドバイザーです。
ステップ1で決定した「中心文」をもとに、志望理由書の「5つの段落」を生徒と一緒に1つずつ肉付け（作成）していきます。

【ステップ1の中心文（ガイドライン）】:
{pasted_center}

【対話の基本方針】：
- 一度に複数の段落を進めず、必ず「まずは第1段落から作っていきましょう」「次は第2段落ですね」と、1つの段落に集中して生徒と対話してください。
- 生徒がその段落に関する高校での出来事や、将来への想いなどを入力したら、以下の【各段落の役割と強くする条件】を満たすように、足りない具体性を優しく問いかけて引き出してください。
- 各段落の文章案がまとまったら、生徒に「〜という文章はいかがですか？」と提案してください。
- 生徒がその提案に「これで決定します」「これでいいです」「これで保存してください」と同意したら、必ず、会話の最後に以下の形式で決定した段落の番号と文章を出力してください。結果以外の余計な文章はタグの後ろに絶対に付けないでください。

[RESULT_P]
NUM: {{段落番号。1から5の半角数字}}
CONTENT: {{決定した段落の文章}}
[/RESULT_P]

【各段落の役割と強くする条件】：
1. 第1段落（きっかけ・問題意識）：興味を持ったきっかけや高校での具体的な体験、授業、探究活動、趣味などの場面をしっかり書かせる。単に「興味がある」という主観的な報告で終わらせない。
2. 第2段落（研究したい問い）：受動的な学び（勉強したい）ではなく、自ら「明らかにしたい具体的な問いや学びたい内容」を問いかけ、調査・実験・データ分析・実技トレーニングなどの手法・方向性を考えさせる。
3. 第3段落（学校理由）：他校ではなく「なぜその大学・専門学校なのか」を説明させる。学校固有の授業名、ゼミ、研究室、地域プログラム、実習、最新設備などの固有名詞を必ず1つ以上入れさせ、研究テーマ・関心と深く結びつけさせる。
4. 第4段落（学び方・将来像）：「学校生活を頑張りたい」といった抽象表現は避け、具体的な行動計画（実習、資格、留学、コンテストなど）を書かせる。また、職業名だけでなく「どのような姿勢や力を持つ人間になりたいか」を明確にする。
5. 第5段落（社会貢献）：「人の役に立つ」という曖昧な表現を完全に排除し、「誰の」「どのような課題に」「どう関わるか」を言葉にして、社会における役割を示させる。
"""

# Gemini 履歴変換用関数（ステップ1用）
def get_gemini_history():
    history = []
    for msg in st.session_state.messages[1:]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({
            "role": role,
            "parts": [msg["content"]]
        })
    return history

# Gemini 履歴変換用関数（ステップ2用）
def get_gemini_history_step2():
    history = []
    for msg in st.session_state.step2_messages[1:]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({
            "role": role,
            "parts": [msg["content"]]
        })
    return history

# Gemini 履歴変換用関数（ステップ4用）
def get_gemini_history_step4():
    history = []
    for msg in st.session_state.step4_messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({
            "role": role,
            "parts": [msg["content"]]
        })
    return history


# --- タブによる4ステップ構成 ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📍 ステップ①：志望理由の核を決める（AI壁打ち）", 
    "✍️ ステップ②：5つの段落に肉付けする（下書き）", 
    "🔍 ステップ③：学校推薦 最終関門チェック（推敲）",
    "💬 ステップ④：模擬面接（面接官AIとの対話練習）"
])

# ==========================================
# --- タブ1: ステップ①：中心文の決定 ---
# ==========================================
with tab1:
    st.header("📍 ステップ①：志望理由の核を一文で決める")
    st.write("「私は何を、どう研究し、将来どう生かしたいのか」の軸（中心文）をAIとの壁打ち対話で決定します。")
    
    col_chat, col_preview = st.columns([3, 2])
    
    with col_chat:
        st.subheader("💬 AI壁打ちチャット")
        
        # APIキーチェック
        if not api_key:
            st.warning("⚠️ AIチャット機能を利用するには、サイドバーでGemini APIキーを入力するか、Streamlit CloudのSecretsに 'GEMINI_API_KEY' を登録してください。")
        
        # チャットコンテナ
        chat_container = st.container(height=400)
        
        # チャット履歴の表示
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    
        # ユーザー入力
        if user_input := st.chat_input("AIに相談する..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with chat_container:
                with st.chat_message("user"):
                    st.write(user_input)
            
            # AIの回答生成
            if api_key:
                with chat_container:
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        with st.spinner("AIがあなたの考えを整理中..."):
                            try:
                                genai.configure(api_key=api_key)
                                model = genai.GenerativeModel(
                                    model_name=selected_model,
                                    system_instruction=system_instruction_step1
                                )
                                chat = model.start_chat(history=get_gemini_history())
                                response = chat.send_message(user_input)
                                ai_response = response.text
                                message_placeholder.write(ai_response)
                                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                                
                                # 結果の自動抽出
                                result_match = re.search(r"\[RESULT\](.*?)\[/RESULT\]", ai_response, re.DOTALL)
                                if result_match:
                                    result_content = result_match.group(1)
                                    theme_m = re.search(r"THEME:\s*(.*)", result_content)
                                    method_m = re.search(r"METHOD:\s*(.*)", result_content)
                                    position_m = re.search(r"POSITION:\s*(.*)", result_content)
                                    target_m = re.search(r"TARGET:\s*(.*)", result_content)
                                    
                                    if theme_m: st.session_state.theme = theme_m.group(1).strip()
                                    if method_m: st.session_state.method = method_m.group(1).strip()
                                    if position_m: st.session_state.position = position_m.group(1).strip()
                                    if target_m: st.session_state.target = target_m.group(1).strip()
                                    
                                    # 中心文を組み立て
                                    st.session_state.step1_sentence = f"私は{st.session_state.theme}について、{st.session_state.method}から研究し、将来{st.session_state.position}として、{st.session_state.target}に貢献したい。"
                                    st.success("🎉 AIとの対話から「中心文」が自動作成されました！右側の調整エリアを確認してコピーしてください。")
                                    st.rerun()
                            except Exception as e:
                                error_msg = f"AIの呼び出し中にエラーが発生しました。APIキーを確認してください。詳細: {e}"
                                message_placeholder.write(error_msg)
                                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                with chat_container:
                    with st.chat_message("assistant"):
                        st.write("🔑 APIキーを設定すると、AIが壁打ちを開始します。")
        
        if st.button("💬 チャットをリセットして最初から相談する"):
            st.session_state.messages = [
                {"role": "assistant", "content": "こんにちは！大学・専門学校の推薦合格を目指して、志望理由書の「核（中心文）」を一緒に固めていきましょう！\n\nまずは、あなたが今高校での探究活動や日常生活の中で、もっとも「疑問に思っていること」や「解決したい地域・社会の課題」について、短くても良いので教えてください！"}
            ]
            st.session_state.theme = ""
            st.session_state.method = ""
            st.session_state.position = ""
            st.session_state.target = ""
            st.session_state.step1_sentence = ""
            st.rerun()

    with col_preview:
        st.subheader("📝 「中心文」の調整と確認")
        st.write("AIとの相談で決まった各要素がここに入ります。直接手動で修正も可能です。")
        
        st.session_state.theme = st.text_input("① 【テーマ】（研究したい具体的な内容）", value=st.session_state.theme)
        st.session_state.method = st.text_input("② 【視点・方法】（どのようなアプローチで研究するか）", value=st.session_state.method)
        st.session_state.position = st.text_input("③ 【立場】（将来活躍したい具体的な職業・役割）", value=st.session_state.position)
        st.session_state.target = st.text_input("④ 【対象・課題】（誰の、どんな課題に貢献したいか）", value=st.session_state.target)
        
        # 手動組み立て
        if st.session_state.theme or st.session_state.method or st.session_state.position or st.session_state.target:
            st.session_state.step1_sentence = f"私は{st.session_state.theme or '（テーマ）'}について、{st.session_state.method or '（視点・方法）'}から研究し、将来{st.session_state.position or '（立場）'}として、{st.session_state.target or '（対象・課題）'}に貢献したい。"
        
        st.markdown("---")
        st.write("👉 **これをコピーして【ステップ②】の「中心文ペースト欄」に貼り付けましょう！**")
        step1_sentence_input = st.text_area("完成した中心文 (一文)", value=st.session_state.step1_sentence, height=80)
        st.session_state.step1_sentence = step1_sentence_input

# ==========================================
# --- タブ2: ステップ②：5つの段落への肉付け ---
# ==========================================
with tab2:
    st.header("✍️ ステップ②：5つの段落に肉付けする")
    st.write("ステップ①で決めた「軸（中心文）」を見つめながら、文章全体の構成をAIと壁打ち相談しながら、または手動で肉付けしていきます。")
    
    # コピペエリア
    st.subheader("🎯 ガイドライン（ステップ①からコピペ）")
    pasted_center = st.text_area(
        "ステップ①で決定した「中心文」をここに貼り付けてください（AI壁打ちチャットと連動します）",
        placeholder="例: 私は地域コミュニティの衰退問題について、自治体と市民の協働という視点から研究し、将来地域コーディネーターとして、高齢化が進む限界集落の維持活性化に貢献したい。",
        height=70,
        value=st.session_state.step1_sentence  # 自動反映
    )
    
    st.markdown("---")
    
    col_step2_chat, col_step2_inputs = st.columns([3, 2])
    
    with col_step2_chat:
        st.subheader("💬 段落作成 AI壁打ちチャット")
        st.write("各段落について、AIと相談しながら文章を練り上げていくことができます。")
        
        if not api_key:
            st.warning("⚠️ AIチャット機能を利用するには、サイドバーでGemini APIキーを入力するか、Streamlit CloudのSecretsに 'GEMINI_API_KEY' を登録してください。")
            
        # チャットコンテナ
        chat_container_step2 = st.container(height=500)
        
        with chat_container_step2:
            for msg in st.session_state.step2_messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    
        # ユーザー入力
        if user_input_step2 := st.chat_input("ステップ2の相談内容を入力する...", key="step2_chat_input"):
            st.session_state.step2_messages.append({"role": "user", "content": user_input_step2})
            with chat_container_step2:
                with st.chat_message("user"):
                    st.write(user_input_step2)
                    
            if api_key:
                with chat_container_step2:
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        with st.spinner("AIが段落のアイデアを整理中..."):
                            try:
                                genai.configure(api_key=api_key)
                                
                                # システムプロンプトに貼り付けられた中心文を埋め込む
                                system_instruction_step2_dynamic = system_instruction_step2.format(pasted_center=pasted_center or "（未設定：ステップ1の中心文を入れてください）")
                                
                                # 履歴変換
                                step2_history = []
                                for msg in st.session_state.step2_messages[1:]:
                                    role = "user" if msg["role"] == "user" else "model"
                                    step2_history.append({"role": role, "parts": [msg["content"]]})
                                    
                                model = genai.GenerativeModel(
                                    model_name=selected_model,
                                    system_instruction=system_instruction_step2_dynamic
                                )
                                chat = model.start_chat(history=step2_history)
                                response = chat.send_message(user_input_step2)
                                ai_response_step2 = response.text
                                message_placeholder.write(ai_response_step2)
                                st.session_state.step2_messages.append({"role": "assistant", "content": ai_response_step2})
                                
                                # 段落結果の自動抽出 [RESULT_P]
                                result_match_p = re.search(r"\[RESULT_P\](.*?)\[/RESULT_P\]", ai_response_step2, re.DOTALL)
                                if result_match_p:
                                    result_content_p = result_match_p.group(1)
                                    num_m = re.search(r"NUM:\s*([1-5])", result_content_p)
                                    content_m = re.search(r"CONTENT:\s*(.*)", result_content_p, re.DOTALL)
                                    
                                    if num_m and content_m:
                                        p_num = num_m.group(1).strip()
                                        p_content = content_m.group(1).strip()
                                        st.session_state[f"step2_p{p_num}"] = p_content
                                        st.success(f"🎉 第 {p_num} 段落の文章が自動反映されました！右側の入力エリアで確認してください。")
                                        st.rerun()
                            except Exception as e:
                                error_msg = f"AIの呼び出し中にエラーが発生しました。詳細: {e}"
                                message_placeholder.write(error_msg)
                                st.session_state.step2_messages.append({"role": "assistant", "content": error_msg})
                                
        if st.button("💬 ステップ2のチャットをリセットする", key="reset_step2_chat"):
            st.session_state.step2_messages = [
                {"role": "assistant", "content": "ステップ①で決めた「中心文」をもとに、5つの段落（きっかけ、研究内容、学校の理由、将来像、社会貢献）を1つずつ一緒に作っていきましょう！\n\nまずは、上部の「ガイドライン貼り付け欄」にステップ①で決めた中心文をペーストしてください。貼り付けたら、どの段落から相談したいか教えてくださいね！"}
            ]
            for i in range(1, 6):
                st.session_state[f"step2_p{i}"] = ""
            st.session_state.step2_compiled = ""
            st.rerun()

    with col_step2_inputs:
        st.subheader("🧱 5段落構成の下書き作成")
        st.write("AIとの相談結果が自動反映されます。直接自分で修正も可能です。")
        
        # 5つの段落設定
        paragraphs_info = [
            {
                "key": "step2_p1",
                "role": "第1段落：きっかけ・問題意識",
                "guide": "【テンプレート】私が【分野】に関心を持ったのは、【経験】がきっかけである。そこから【課題】に疑問を持った。",
                "condition": "💡 **推薦を強くする条件**:\n\n高校での具体的な体験、授業、探究活動、趣味などの場面をしっかり書きましょう。単に「興味がある」という主観的な報告で終わらせないことが極めて重要です。"
            },
            {
                "key": "step2_p2",
                "role": "第2段落：研究・学びたい内容",
                "guide": "【テンプレート】大学・専門学校では【テーマ】について、【方法・視点】から明らかにしたい。特に【具体的な問い】に関心がある。",
                "condition": "💡 **推薦を強くする条件**:\n\n単なる「受動的な勉強（学びたい）」ではなく、自ら「明らかにしたい具体的な問いや学びたい内容」を問いかけ、調査・実験・データ分析・実習などの手法・方向性を考えさせる。"
            },
            {
                "key": "step2_p3",
                "role": "第3段落：その学校である理由（最重要）",
                "guide": "【テンプレート】貴校の【授業・ゼミ・コース等】では、【できる学び】に取り組める。これは、私の【関心】を深めるうえで必要である。",
                "condition": "💡 **推薦を強くする条件**:\n\n他校の同種学部・コースではなく「なぜその学校なのか」を説明します。学校固有の授業名、ゼミ、研究室、実習、カリキュラム、地域プログラムなどの**固有名詞を必ず1つ以上**入れ、自分の研究テーマ・学びたいことと結びつけましょう。"
            },
            {
                "key": "step2_p4",
                "role": "第4段落：入学後の学び方／将来像",
                "guide": "【テンプレート】入学後は【取り組み】に挑戦し、【力】を身につけたい。そして、将来は【立場】として【どのように働くか】できる人間になりたい。",
                "condition": "💡 **推薦を強くする条件**:\n\n「学校生活を頑張りたい」といった抽象表現は避け、具体的な行動計画（実習、資格、留学、コンテストなど）を記述します。また、職業名だけでなく「どのような姿勢や力を持つ人間になりたいか」を明確にします。"
            },
            {
                "key": "step2_p5",
                "role": "第5段落：社会貢献",
                "guide": "【テンプレート】将来は【身につけた力】を活かして、【対象・課題】に関わる形で社会に貢献したい。",
                "condition": "💡 **推薦を強くする条件**:\n\n「人の役に立つ」という曖昧な表現を完全に排除します。「誰の」「どのような課題に」「どう関わるか」を言葉にして、社会における自分の役割を示します。"
            }
        ]
        
        # 5段落の入力フォーム
        p_texts = []
        for p in paragraphs_info:
            st.subheader(p["role"])
            st.caption(p["guide"])
            p_val = st.text_area(
                "下書き入力エリア",
                value=st.session_state[p["key"]],
                key=f"{p['key']}_input",
                height=120,
                label_visibility="collapsed"
            )
            st.session_state[p["key"]] = p_val
            p_texts.append(p_val)
            st.caption(f"文字数: {len(p_val)} 文字")
            
            # 各段落ごとのローカルリアルタイムルールチェック
            if p_val:
                warnings = analyze_text(p_val)
                for w in warnings:
                    st.write(w)
            st.markdown("---")
            
        # 5段落の結合プレビュー
        st.subheader("📝 5段落を統合した完成原稿案")
        compiled_draft = "\n\n".join([st.session_state[f"step2_p{i}"] for i in range(1, 6) if st.session_state[f"step2_p{i}"]])
        st.session_state.step2_compiled = compiled_draft
        
        st.write("👉 **これをコピーして【ステップ③】の「最終添削ペースト欄」に貼り付けましょう！**")
        st.text_area(
            "統合された下書きテキスト",
            value=st.session_state.step2_compiled,
            height=250,
            key="step2_compiled_area"
        )
        if compiled_draft:
            st.caption(f"全体の文字数: {len(compiled_draft)} 文字 (改行を含む)")

# ==========================================
# --- タブ3: ステップ③：学校推薦 最終関門チェック ---
# ==========================================
with tab3:
    st.header("🔍 ステップ③：学校推薦 最終関門チェック（推敲）")
    st.write("ステップ②で肉付けした下書きをコピペし、大学・専門学校の推薦指導基準に基づく「厳しいAIチェック」と「詳細な自己診断」を行います。")
    
    # 下書きコピペエリア
    st.subheader("📥 最終添削ペースト欄（ステップ②からコピペ）")
    step3_input_text = st.text_area(
        "ステップ②で統合した文章、または現在の志望理由書をここに貼り付けてください：",
        value=st.session_state.step3_input,
        placeholder="ここに文章を貼り付けると、下に自動でエラーチェックとチェックリストが表示されます。",
        height=250,
        key="step3_input_area"
    )
    st.session_state.step3_input = step3_input_text
    
    if step3_input_text:
        st.caption(f"現在の入力文字数: {len(step3_input_text)} 文字")
        
        # 1. プログラムによる基本ルール自動検知
        st.subheader("🚨 基本ルール違反検知（リアルタイム）")
        failures = analyze_text(step3_input_text)
        if failures:
            for f_msg in failures:
                st.markdown(f_msg)
        else:
            st.success("✅ 抽象表現の不使用、一文60文字制限など、基本表記ルールをすべてクリアしています！")
            
        st.markdown("---")
        
        # 2. AIによる学校推薦 厳格添削
        st.subheader("🤖 AI大学・専門学校推薦 厳格添削フィードバック")
        st.write("学校推薦や総合型選抜で勝負できる文章か、学校の求めるAP（アドミッション・ポリシー）や他校との差別化ができているかをAIが徹底分析します。")
        
        if not api_key:
            st.warning("🔑 AI厳格添削を利用するには、サイドバーでGemini APIキーを設定してください。")
        else:
            if st.button("🔥 AIによる『学校推薦 厳格添削』を実行する"):
                with st.spinner("進路指導アドバイザーが文章を厳しく添削中..."):
                    try:
                        genai.configure(api_key=api_key)
                        
                        system_instruction_step3 = """あなたは大学や専門学校の学校推薦型選抜や総合型選抜の指導で、毎年数多くの合格者を輩出している超一流の進路指導教諭です。
生徒が書いた志望理由書の全文を読み、以下の厳しい推薦指導の観点（特にアドミッション・ポリシーへの合致や、他校ではなく『その学校で学ぶ必然性』）から評価し、具体的な赤ペン添削と改善アクションを提示してください。

【評価の極意（添削基準）】：
1. AP（アドミッションポリシー）や求める学生像の丸写しがないか：「APに共感した」「求める人物像に合致している」といった手抜きの表現は絶対に不合格になります。生徒自身の経験と言葉でそれが示せているか。
2. その学校である理由の「必然性」：学校名だけを他校に置き換えても意味が通じる場合は、容赦なく「具体性不足」と指摘してください。授業名、ゼミ、研究室、実習、カリキュラムなどの固有名詞が、本人の学びたい内容と本当に結びついているか。
3. 受動的な「勉強したい」になっていないか：学校を単なる「教えてもらう場所」と考えている甘い姿勢がないか。自ら「問い」を立てて主体的に研究・学習・実習する姿勢があるか。
4. 表現の厳格さ：「魅力を感じた」「さまざまな」といった具体性のない言葉や、一文が長すぎて何を言いたいか分からない箇所（60文字超）がないか。

【出力フォーマット】：
## 🌟 推薦・総合型選抜 総合評価
[A（このまま出願可能） / B（あと一歩の修正が必要） / C（大幅な見直しが必要）]

## 🔴 厳しい指摘（ここが推薦の合格基準に達していません！）
- （1つ〜3つ、具体的にどの文章がどう甘いかを厳しく、しかし熱意を持って指摘してください）

## ✏️ 劇的に強くなる！赤ペン添削・書き換え具体案
- 【現状の文】:「...」
- 【改善案】:「...」
- 【解説】: なぜこのように書き換えるべきか、生徒の経験や固有名詞をどう引き出すかのヒント。

## 💡 次のステップへのアドバイス
- 生徒が明日からすぐに書き直せるような温かい激励メッセージ。
"""
                        model = genai.GenerativeModel(
                            model_name=selected_model,
                            system_instruction=system_instruction_step3
                        )
                        response = model.generate_content(
                            f"【生徒の志望理由書】:\n{step3_input_text}\n\n上記を添削してください。"
                        )
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"AI添削中にエラーが発生しました。詳細: {e}")
                        
        st.markdown("---")
        
        # 3. デジタル自己評価・相互評価チェックリスト
        st.subheader("📋 志望理由書 完成原稿チェックリスト")
        st.write("できている＝○（達成）、弱い＝△（やや弱い）、直す＝×（未達成）でチェック。△・×の項目は手動で文章をブラッシュアップしましょう。")
        
        checklist_items = [
            {"cat": "個別性", "item": "学校名（大学・専門学校名）を他校に置き換えても不自然にならないくらい、その学校固有の理由がある。"},
            {"cat": "個別性", "item": "授業名・ゼミ・研究室・実習・カリキュラム・設備などの固有名詞を、ただ挙げるだけでなく自分のテーマと結びつけている。"},
            {"cat": "研究内容", "item": "「何を学びたいか」が、学問名や分野名だけでなく具体的な問い・課題として書かれている。"},
            {"cat": "研究内容", "item": "学びたい内容について、調査・実験・比較・データ分析・フィールドワーク・実習など、学び方の具体的な方向が見える。"},
            {"cat": "経験", "item": "高校での経験は活動報告で終わらず、「そこから何に気づいたか」「なぜこの学校で深めたいか」につながっている。"},
            {"cat": "経験", "item": "「昔から好きだった」「興味がある」だけでなく、関心が深まった具体的な場面がある。"},
            {"cat": "将来像", "item": "将来像が職業名だけで終わらず、どのような姿勢や力を持つ人間になりたいかが書かれている。"},
            {"cat": "社会貢献", "item": "「人の役に立つ」「社会に貢献する」を、誰の・どのような課題に・どう関わるかに言い換えられている。"},
            {"cat": "一貫性", "item": "きっかけ、学びたいこと、その学校である理由、将来像、社会貢献が一本の線でつながっている。"},
            {"cat": "AP", "item": "APの文言を写したり、「APに共感した」と書いたりせず、求める学生像に合う自分の経験・姿勢で示している。"},
            {"cat": "表現", "item": "学校紹介や制度説明が長くなりすぎず、主語が自分になっている。"},
            {"cat": "表現", "item": "「魅力を感じた」「さまざまな」「多くのこと」「視野を広げる」などの抽象表現を、具体的な内容に直している。"},
            {"cat": "表現", "item": "一文が長すぎない。目安として一文60字を超える文は、二文に分けられないか確認している。"}
        ]
        
        for idx, item in enumerate(checklist_items):
            col_lbl, col_rad = st.columns([4, 2])
            with col_lbl:
                st.write(f"**[{item['cat']}]** {item['item']}")
            with col_rad:
                st.radio(
                    f"評価_{idx}",
                    ["未達成 (×)", "やや弱い (△)", "達成 (○)"],
                    key=f"final_eval_{idx}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
    else:
        st.info("ステップ②で作成した「統合された下書きテキスト」をコピーし、上の入力欄に貼り付けると、AI厳密添削やチェックリスト機能が起動します。")

# ==========================================
# --- タブ4: ステップ④：模擬面接 ---
# ==========================================
with tab4:
    st.header("💬 ステップ④：模擬面接（面接官AIとの対話練習）")
    st.write("ステップ③で完成した志望理由書を提出したと仮定し、面接官AIと本番さながらの模擬面接（口頭試問を含む）を行います。回答内容に対する厳しい突っ込みを切り抜ける練習をし、最後には詳しい評価とアドバイスがもらえます。")
    
    # 志望理由書が貼り付けられているかチェック
    if not st.session_state.step3_input:
        st.warning("⚠️ まだステップ③の「最終添削ペースト欄」に志望理由書が貼り付けられていません。まずはステップ③のペースト欄に現在の志望理由書を貼り付けてから、この面接ステップに進んでください。")
    else:
        # 面接の初期設定
        if not st.session_state.step4_messages:
            st.session_state.step4_messages = [
                {"role": "assistant", "content": "それでは、これより模擬面接を開始します。あなたの志望理由書は事前に読み込んでおります。本番だと思って緊張感を持って挑んでくださいね。\n\n準備ができたら「お願いします」と入力するか、面接への意気込みを一言入力して、対話を開始してください。"}
            ]
            st.session_state.step4_active = True
            st.session_state.step4_feedback = ""

        # AIステップ4用のシステムプロンプト (面接官AI)
        system_instruction_step4 = f"""あなたは、大学または専門学校の推薦入試・総合型選抜（AO入試）の面接を行う、面接官（教員、教授、または入試担当者）です。
生徒が提出した以下の「志望理由書」を熟読した上で、本番さながらの模擬面接を実施してください。

【生徒が提出した志望理由書】：
{st.session_state.step3_input}

【面接官としての指導ルール】：
1. 入試本番の緊迫感を持たせるため、丁寧でありながらも、真剣かつ少し厳格な口調（「〜ですね」「〜について具体的に教えてください」）で対話してください。
2. 一度に複数の質問を投げず、必ず1つずつ質問してください。
3. 生徒の回答をよく聴き、その回答内容をさらに深掘りする質問をしてください（例: 「高校でのその経験から、どのような気付きがありましたか？」「本校の〇〇という授業に興味があるとのことですが、他校ではなくなぜ本校のその授業なのですか？」など）。
4. 質問は全部で3〜4問程度を目安とし、志望理由書の核心（動機、研究/学びの問い、その学校である理由、将来の計画）を網羅してください。
5. 生徒が「フィードバックをお願いします」と言った場合、またはシステムから終了指示（[FORCE_FEEDBACK]）が送られた場合は、対話を打ち切り、必ず以下の【終了時のフィードバック出力フォーマット】にのみ従って、詳しい評価とアドバイスを日本語で出力してください。

【終了時のフィードバック出力フォーマット】:
[FEEDBACK]
### 🌟 模擬面接 総合評価
[A（合格圏内） / B（あと一歩の努力が必要） / C（要練習・大幅な見直しが必要）]

### 良かった点（あなたの強み）
- （生徒の回答の良かった点を2〜3つ、具体的に記述してください）

### 改善すべき点（こう答えればもっと響く！）
- （回答の弱かった点や、より具体的に伝えるべきだった点を2〜3つ、具体的な改善例とともに記述してください）

### 本番に向けたアドバイス
- （本番の面接に向けて、自信を持って臨むためのアドバイスや心構えを熱意を持って伝えてください）
[/FEEDBACK]
"""

        col_step4_chat, col_step4_ref = st.columns([3, 2])
        
        with col_step4_ref:
            st.subheader("📋 あなたの志望理由書（参考）")
            st.info(st.session_state.step3_input)
            
            st.markdown("---")
            st.subheader("🏁 面接の終了とフィードバック")
            st.write("十分に受け答えが完了したと感じたら、以下のボタンを押して面接官からの最終フィードバック（評価と赤ペンアドバイス）を確認しましょう。")
            
            if st.button("🔥 面接を終了してフィードバックをもらう", key="end_interview_btn"):
                if api_key:
                    with st.spinner("面接官があなたのアピールを評価中..."):
                        try:
                            genai.configure(api_key=api_key)
                            model = genai.GenerativeModel(
                                model_name=selected_model,
                                system_instruction=system_instruction_step4
                            )
                            # 対話履歴に強制終了のプロンプトを投げる
                            st.session_state.step4_messages.append({"role": "user", "content": "[FORCE_FEEDBACK] 面接を終了して、フォーマットに従って詳細なフィードバックを出力してください。"})
                            chat = model.start_chat(history=get_gemini_history_step4())
                            response = chat.send_message("[FORCE_FEEDBACK]")
                            feedback_text = response.text
                            st.session_state.step4_feedback = feedback_text
                            st.session_state.step4_active = False
                            st.session_state.step4_messages.append({"role": "assistant", "content": feedback_text})
                            st.rerun()
                        except Exception as e:
                            st.error(f"フィードバック生成中にエラーが発生しました: {e}")
                else:
                    st.warning("🔑 フィードバックを生成するにはAPIキーが必要です。")
                    
            if st.session_state.step4_feedback:
                st.success("📝 面接官からのフィードバックが届きました！")
                
                # [FEEDBACK] タグをきれいに見せる
                clean_feedback = st.session_state.step4_feedback.replace("[FEEDBACK]", "").replace("[/FEEDBACK]", "")
                st.markdown(clean_feedback)

        with col_step4_chat:
            st.subheader("💬 模擬面接チャット")
            
            if not api_key:
                st.warning("⚠️ 模擬面接チャットを利用するには、サイドバーでGemini APIキーを設定してください。")
            
            # チャットコンテナ
            chat_container_step4 = st.container(height=500)
            
            with chat_container_step4:
                for msg in st.session_state.step4_messages:
                    # FORCE_FEEDBACKシステムメッセージは非表示にする
                    if "[FORCE_FEEDBACK]" in msg["content"]:
                        continue
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                        
            # ユーザーの回答入力
            if user_reply := st.chat_input("面接官に回答する...", key="step4_chat_input", disabled=not st.session_state.step4_active):
                st.session_state.step4_messages.append({"role": "user", "content": user_reply})
                with chat_container_step4:
                    with st.chat_message("user"):
                        st.write(user_reply)
                        
                if api_key:
                    with chat_container_step4:
                        with st.chat_message("assistant"):
                            message_placeholder_step4 = st.empty()
                            with st.spinner("面接官がうなずいています..."):
                                try:
                                    genai.configure(api_key=api_key)
                                    model = genai.GenerativeModel(
                                        model_name=selected_model,
                                        system_instruction=system_instruction_step4
                                    )
                                    chat = model.start_chat(history=get_gemini_history_step4())
                                    response = chat.send_message(user_reply)
                                    ai_reply = response.text
                                    
                                    # もしAIが自律的に [FEEDBACK] を出してきた場合、終了状態にする
                                    if "[FEEDBACK]" in ai_reply:
                                        st.session_state.step4_feedback = ai_reply
                                        st.session_state.step4_active = False
                                        
                                    message_placeholder_step4.write(ai_reply)
                                    st.session_state.step4_messages.append({"role": "assistant", "content": ai_reply})
                                    if not st.session_state.step4_active:
                                        st.rerun()
                                except Exception as e:
                                    error_msg = f"面接官AIの応答中にエラーが発生しました: {e}"
                                    message_placeholder_step4.write(error_msg)
                                    st.session_state.step4_messages.append({"role": "assistant", "content": error_msg})
                                    
            if st.button("💬 模擬面接を最初からやり直す", key="reset_step4_btn"):
                st.session_state.step4_messages = []
                st.session_state.step4_active = True
                st.session_state.step4_feedback = ""
                st.rerun()
